import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { EnvironmentConfig } from '../types/environment';
import { CloudWatchLogGroups } from '../constructs/cloudwatch';
import { LambdaExecutionRole } from '../constructs/iam';
import { LambdaFunction } from '../constructs/lambda';
import { Duration } from 'aws-cdk-lib';
import * as path from 'path';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import { SqsEventSource } from 'aws-cdk-lib/aws-lambda-event-sources';
import { ApiGateway } from '../constructs/apigateway';
import * as apigateway from 'aws-cdk-lib/aws-apigatewayv2';
import { HttpLambdaIntegration } from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import * as fs from 'fs';
import { execFileSync } from 'child_process';

export interface ComputeStackProps extends EnvironmentConfig {
    assetBucket: s3.IBucket;
    assetBucketKmsKey: kms.IKey;
    sessionTable: dynamodb.ITableV2;
    sessionTableKmsKey: kms.IKey;
    assetQueue: sqs.IQueue;
    bedrockGuardrailID: string;
    bedrockGuardrailVersion: string;
    stepFunctionsBucket: s3.IBucket;
    stepFunctionsBucketKmsKey: kms.IKey;
    samEndpointName: string;
    samEndpointArn: string;
}

interface LambdaParams {
    id: string;
    runtime: lambda.Runtime;
    handlerName: string;
    codePath: string;
    timeoutInSeconds?: number;
    memorySize?: number;
    layerEnabled?: boolean;
    environment?: Record<string, string>,
    stepFunctionArns?: string[],
    sageMakerArns?: string[],
    bedrockIntegration?: boolean,
    pipelineLayer?: boolean
}

/**
 * Shared layer for the five pipeline Lambdas: numpy + Pillow (manylinux wheels for
 * python3.13/x86_64) and the `woundlib` package. Bundled locally with pip when
 * possible (no Docker needed), otherwise in the Lambda build image via Docker.
 */
function pipelineLayerCode(sharedDir: string): lambda.Code {
    return lambda.Code.fromAsset(sharedDir, {
        exclude: ['**/__pycache__', '**/*.pyc'],
        bundling: {
            image: lambda.Runtime.PYTHON_3_13.bundlingImage,
            command: ['bash', '-c',
                'pip install --no-cache-dir -r requirements.txt -t /asset-output/python && cp -r woundlib /asset-output/python/'],
            local: {
                tryBundle(outputDir: string): boolean {
                    const python = process.env.PYTHON ?? (process.platform === 'win32' ? 'python' : 'python3');
                    try {
                        execFileSync(python, ['-m', 'pip', 'install', '--quiet', '--disable-pip-version-check',
                            '--no-deps', '--isolated', '--no-warn-conflicts',
                            '--only-binary=:all:', '--python-version', '3.13', '--implementation', 'cp',
                            '--platform', 'manylinux_2_28_x86_64', '--platform', 'manylinux2014_x86_64',
                            '--target', path.join(outputDir, 'python'),
                            '-r', path.join(sharedDir, 'requirements.txt')], { stdio: 'inherit' });
                    } catch (e) {
                        return false;   // fall back to Docker bundling
                    }
                    fs.cpSync(path.join(sharedDir, 'woundlib'), path.join(outputDir, 'python', 'woundlib'), {
                        recursive: true,
                        filter: (src) => !src.includes('__pycache__')
                    });
                    return true;
                }
            }
        }
    });
}

export class ComputeStack extends cdk.Stack {
    public readonly preprocessLambda: lambda.Function;
    public readonly segmentLambda: lambda.Function;
    public readonly computeLambda: lambda.Function;
    public readonly generateDiagramsLambda: lambda.Function;
    public readonly narrateLambda: lambda.Function;

    constructor(scope: Construct, id: string, props: ComputeStackProps) {
        super(scope, id, { env: { account: props.account, region: props.region } });
        cdk.Tags.of(this).add('Workspace', 'IaC/Compute');
        cdk.Tags.of(this).add('Env', props.environment);
        cdk.Tags.of(this).add('CDK', 'true');

        const identifier = `${props.identifier}-${props.environment}`;

        // ================= SHARED PIPELINE LAYER =================
        const pipelineLayer = new lambda.LayerVersion(this, 'PipelineDepsLayer', {
            layerVersionName: `${identifier}-pipeline-deps`,
            code: pipelineLayerCode(path.join(__dirname, '../../../Backend/lambdas/step_functions/shared')),
            compatibleRuntimes: [lambda.Runtime.PYTHON_3_13],
            compatibleArchitectures: [lambda.Architecture.X86_64],
            description: 'numpy + Pillow + woundlib for the wound-scan pipeline steps'
        });

        // ==================== LAMBDA FUNCTIONS ====================
        const makeLambda = (params: LambdaParams) => {
            
            const functionName = `${params.id}-${props.environment}`.toLowerCase();

            // ================== CLOUDWATCH LOG GROUPS ==================
            const logGroup = new CloudWatchLogGroups(this, `${params.id}LogGroup`, {
                logGroupResource: "lambda",
                logGroupName: functionName,
                retentionDays: logs.RetentionDays.ONE_MONTH,
            });
            // ======================== IAM ROLES ========================
            const lambdaExecutionRole = new LambdaExecutionRole(this, `${params.id}ExecutionRole`, {
                identifier: `${functionName}-role`,
                logGroup: logGroup.logGroup,
                stepFunctionArns: params.stepFunctionArns,
                sageMakerEndpointArns: params.sageMakerArns,
                bedrockIntegration: params.bedrockIntegration ?? false
            });

            return new LambdaFunction(this, params.id, {
                functionName: functionName,
                runtime: params.runtime,
                handler: params.handlerName,
                code: lambda.Code.fromAsset(path.join(__dirname, '../../../', params.codePath)),
                timeout: Duration.seconds(params.timeoutInSeconds ?? 30),
                memorySize: params.memorySize ?? 128,
                role: lambdaExecutionRole.role,
                logGroup: logGroup.logGroup,
                layerEnabled: params.layerEnabled ?? false,
                layers: params.pipelineLayer ? [pipelineLayer] : undefined,
                environment: params.environment ?? {}
            });
        }

        // Pipeline steps read the capture bundle from / write results to the assets
        // bucket, and keep intermediates (work/{scanId}/...) in the Step Functions state bucket.
        const pipelineEnv: Record<string, string> = {
            STATE_BUCKET: props.stepFunctionsBucket.bucketName
        };
        const grantPipelineAccess = (fn: lambda.Function) => {
            props.assetBucket.grantReadWrite(fn);
            props.assetBucketKmsKey.grantEncryptDecrypt(fn);
            props.stepFunctionsBucket.grantReadWrite(fn);
            props.stepFunctionsBucketKmsKey.grantEncryptDecrypt(fn);
        };

        const apiHandlerLambda = makeLambda({
            id: props.compute.apiHandlerLambda.functionName, 
            runtime: props.compute.apiHandlerLambda.runtime,
            handlerName: props.compute.apiHandlerLambda.handlerName,
            codePath: props.compute.apiHandlerLambda.codePath,
            timeoutInSeconds: props.compute.apiHandlerLambda.timeoutInSeconds,
            memorySize: props.compute.apiHandlerLambda.memorySize,
            layerEnabled: props.compute.apiHandlerLambda.layerEnabled,
            stepFunctionArns: [`arn:aws:states:${props.region}:${props.account}:stateMachine:${identifier}-${props.stepFunctions.stateMachineName}`]
        });
        props.assetBucket.grantReadWrite(apiHandlerLambda.lambda);
        props.assetBucketKmsKey.grantDecrypt(apiHandlerLambda.lambda);
        props.sessionTable.grantReadWriteData(apiHandlerLambda.lambda);
        props.sessionTableKmsKey.grantDecrypt(apiHandlerLambda.lambda);

        const uploadCoordinatorLambda = makeLambda({
            id: props.compute.uploadCoordinatorLambda.functionName, 
            runtime: props.compute.uploadCoordinatorLambda.runtime,
            handlerName: props.compute.uploadCoordinatorLambda.handlerName,
            codePath: props.compute.uploadCoordinatorLambda.codePath,
            timeoutInSeconds: props.compute.uploadCoordinatorLambda.timeoutInSeconds,
            memorySize: props.compute.uploadCoordinatorLambda.memorySize,
            layerEnabled: props.compute.uploadCoordinatorLambda.layerEnabled,
            stepFunctionArns: [`arn:aws:states:${props.region}:${props.account}:stateMachine:${identifier}-${props.stepFunctions.stateMachineName}`]
        });
        // Counts uploaded frames (s3:ListBucket) before starting the workflow.
        props.assetBucket.grantRead(uploadCoordinatorLambda.lambda);
        props.assetBucketKmsKey.grantDecrypt(uploadCoordinatorLambda.lambda);
        uploadCoordinatorLambda.lambda.addEventSource(new SqsEventSource(props.assetQueue, {
            batchSize: 10
        }));
        props.sessionTable.grantReadWriteData(uploadCoordinatorLambda.lambda);
        props.sessionTableKmsKey.grantDecrypt(uploadCoordinatorLambda.lambda);

        // ===================== STEP FUNCTIONS LAMBDAS =====================
        const preprocessLambda = makeLambda({
            id: props.compute.preprocessLambda.functionName, 
            runtime: props.compute.preprocessLambda.runtime,
            handlerName: props.compute.preprocessLambda.handlerName,
            codePath: props.compute.preprocessLambda.codePath,
            timeoutInSeconds: props.compute.preprocessLambda.timeoutInSeconds,
            memorySize: props.compute.preprocessLambda.memorySize,
            layerEnabled: props.compute.preprocessLambda.layerEnabled,
            pipelineLayer: props.compute.preprocessLambda.pipelineLayer,
            environment: { ...pipelineEnv, ...(props.compute.preprocessLambda.environment ?? {}) }
        });
        grantPipelineAccess(preprocessLambda.lambda);
        props.sessionTable.grantReadWriteData(preprocessLambda.lambda);
        props.sessionTableKmsKey.grantDecrypt(preprocessLambda.lambda);

        
        const sageMakerEndpointARN: string[] = [props.samEndpointArn];
        const segmentLambda = makeLambda({
            id: props.compute.segmentLambda.functionName, 
            runtime: props.compute.segmentLambda.runtime,
            handlerName: props.compute.segmentLambda.handlerName,
            codePath: props.compute.segmentLambda.codePath,
            timeoutInSeconds: props.compute.segmentLambda.timeoutInSeconds,
            memorySize: props.compute.segmentLambda.memorySize,
            layerEnabled: props.compute.segmentLambda.layerEnabled,
            pipelineLayer: props.compute.segmentLambda.pipelineLayer,
            environment: {
                ...pipelineEnv,
                SAGEMAKER_ENDPOINT_NAME: props.samEndpointName,
                SAGEMAKER_ENDPOINT_ARN: props.samEndpointArn,
                ...(props.compute.segmentLambda.environment ?? {})
            },
            sageMakerArns: sageMakerEndpointARN
        });
        grantPipelineAccess(segmentLambda.lambda);
        props.sessionTable.grantReadWriteData(segmentLambda.lambda);
        props.sessionTableKmsKey.grantDecrypt(segmentLambda.lambda);

        const computeLambda = makeLambda({
            id: props.compute.computeLambda.functionName, 
            runtime: props.compute.computeLambda.runtime,
            handlerName: props.compute.computeLambda.handlerName,
            codePath: props.compute.computeLambda.codePath,
            timeoutInSeconds: props.compute.computeLambda.timeoutInSeconds,
            memorySize: props.compute.computeLambda.memorySize,
            layerEnabled: props.compute.computeLambda.layerEnabled,
            pipelineLayer: props.compute.computeLambda.pipelineLayer,
            environment: { ...pipelineEnv, ...(props.compute.computeLambda.environment ?? {}) }
        });
        grantPipelineAccess(computeLambda.lambda);
        props.sessionTable.grantReadWriteData(computeLambda.lambda);
        props.sessionTableKmsKey.grantDecrypt(computeLambda.lambda);

        const generateDiagramsLambda = makeLambda({
            id: props.compute.generateDiagramsLambda.functionName, 
            runtime: props.compute.generateDiagramsLambda.runtime,
            handlerName: props.compute.generateDiagramsLambda.handlerName,
            codePath: props.compute.generateDiagramsLambda.codePath,
            timeoutInSeconds: props.compute.generateDiagramsLambda.timeoutInSeconds,
            memorySize: props.compute.generateDiagramsLambda.memorySize,
            layerEnabled: props.compute.generateDiagramsLambda.layerEnabled,
            pipelineLayer: props.compute.generateDiagramsLambda.pipelineLayer,
            environment: { ...pipelineEnv, ...(props.compute.generateDiagramsLambda.environment ?? {}) }
        });
        grantPipelineAccess(generateDiagramsLambda.lambda);
        props.sessionTable.grantReadWriteData(generateDiagramsLambda.lambda);
        props.sessionTableKmsKey.grantDecrypt(generateDiagramsLambda.lambda);

        const narrateEnvVars: Record<string,string> = {
            "BEDROCK_GUARDRAIL_ID": props.bedrockGuardrailID,
            "BEDROCK_GUARDRAIL_VERSION": props.bedrockGuardrailVersion,
            "NARRATE_MODEL_IDS": props.ai.narration.modelIds,
            ...pipelineEnv
        }

        const narrateLambda = makeLambda({
            id: props.compute.narrateLambda.functionName, 
            runtime: props.compute.narrateLambda.runtime,
            handlerName: props.compute.narrateLambda.handlerName,
            codePath: props.compute.narrateLambda.codePath,
            timeoutInSeconds: props.compute.narrateLambda.timeoutInSeconds,
            memorySize: props.compute.narrateLambda.memorySize,
            layerEnabled: props.compute.narrateLambda.layerEnabled,
            environment: narrateEnvVars,
            bedrockIntegration: true,
            pipelineLayer: props.compute.narrateLambda.pipelineLayer
        });
        grantPipelineAccess(narrateLambda.lambda);
        props.sessionTable.grantReadWriteData(narrateLambda.lambda);
        props.sessionTableKmsKey.grantDecrypt(narrateLambda.lambda);


        const scansGateway = new ApiGateway(this, 'ApiGateway', {
            apiName: `${identifier}-scans-gateway`,
            apiDescription: "REST API for Albacete Meddev scans application."
        });
        const apiHandlerLambdaIntegration = new HttpLambdaIntegration('ApiHandlerIntegration', apiHandlerLambda.lambda);

        scansGateway.apiGateway.addRoutes({
            integration: apiHandlerLambdaIntegration,
            path: "/scans",
            methods: [apigateway.HttpMethod.POST]
        });

        scansGateway.apiGateway.addRoutes({
            integration: apiHandlerLambdaIntegration,
            path: "/scans/{scanId}/status",
            methods: [apigateway.HttpMethod.GET]
        });

        scansGateway.apiGateway.addRoutes({
            integration: apiHandlerLambdaIntegration,
            path: "/scans/{scanId}/results",
            methods: [apigateway.HttpMethod.GET]
        });
        
        this.preprocessLambda = preprocessLambda.lambda;
        this.segmentLambda = segmentLambda.lambda;
        this.computeLambda = computeLambda.lambda;
        this.generateDiagramsLambda = generateDiagramsLambda.lambda;
        this.narrateLambda = narrateLambda.lambda;
    }
}
