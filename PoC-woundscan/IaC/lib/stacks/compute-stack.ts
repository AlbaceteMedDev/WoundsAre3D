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

export interface ComputeStackProps extends EnvironmentConfig {
    assetBucket: s3.IBucket;
    assetBucketKmsKey: kms.IKey;
    sessionTable: dynamodb.ITableV2;
    sessionTableKmsKey: kms.IKey;
    assetQueue: sqs.IQueue;
    bedrockGuardrailID: string;
    bedrockGuardrailVersion: string;
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
    bedrockIntegration?: boolean
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
                environment: params.environment ?? {}
            });
        }

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
        });
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
        });
        props.sessionTable.grantReadWriteData(preprocessLambda.lambda);
        props.sessionTableKmsKey.grantDecrypt(preprocessLambda.lambda);

        
        const sageMakerEndpointARN: string[] = (props.compute.segmentLambda.environment?.["SAGEMAKER_ENDPOINT_ARN"])
            ? [props.compute.segmentLambda.environment["SAGEMAKER_ENDPOINT_ARN"]]
            : [];
        const segmentLambda = makeLambda({
            id: props.compute.segmentLambda.functionName, 
            runtime: props.compute.segmentLambda.runtime,
            handlerName: props.compute.segmentLambda.handlerName,
            codePath: props.compute.segmentLambda.codePath,
            timeoutInSeconds: props.compute.segmentLambda.timeoutInSeconds,
            memorySize: props.compute.segmentLambda.memorySize,
            layerEnabled: props.compute.segmentLambda.layerEnabled,
            environment: props.compute.segmentLambda.environment,
            sageMakerArns: sageMakerEndpointARN
        });
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
        });
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
        });
        props.sessionTable.grantReadWriteData(generateDiagramsLambda.lambda);
        props.sessionTableKmsKey.grantDecrypt(generateDiagramsLambda.lambda);

        const narrateEnvVars: Record<string,string> = {
            "BEDROCK_GUARDRAIL_ID": props.bedrockGuardrailID,
            "BEDROCK_GUARDRAIL_VERSION": props.bedrockGuardrailVersion
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
            bedrockIntegration: true
        });
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
