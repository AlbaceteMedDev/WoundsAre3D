import * as fs from 'fs';
import * as path from 'path';
import { Construct } from 'constructs';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as s3assets from 'aws-cdk-lib/aws-s3-assets';
import * as sagemaker from 'aws-cdk-lib/aws-sagemaker';
import { SageMakerExecutionRole } from './iam';

export interface SamServerlessEndpointProps {
    identifier: string;
    endpointName: string;
    image: string;
    modelArtifactFile: string;
    logGroupName: string;
    memorySizeInMb: number;
    maxConcurrency: number;
}

/**
 * SAM ViT-B on a SageMaker Serverless Inference endpoint (CPU, pay per request,
 * no idle cost). The model artifact is built by Backend/sagemaker/sam/build_model.py
 * and uploaded as a CDK asset.
 */
export class SamServerlessEndpoint extends Construct {
    public readonly endpointName: string;
    public readonly endpointArn: string;

    constructor(scope: Construct, id: string, props: SamServerlessEndpointProps) {
        super(scope, id);

        if (!fs.existsSync(props.modelArtifactFile)) {
            throw new Error(
                `SAM model artifact not found: ${props.modelArtifactFile}\n` +
                `Build it first: python ${path.join('Backend', 'sagemaker', 'sam', 'build_model.py')}`
            );
        }

        const artifact = new s3assets.Asset(this, 'ModelArtifact', { path: props.modelArtifactFile });
        const logGroup = logs.LogGroup.fromLogGroupName(this, 'EndpointLogs', props.logGroupName);

        const role = new SageMakerExecutionRole(this, 'ExecutionRole', {
            identifier: `${props.identifier}-sam`,
            logGroup,
            s3BucketArns: [],
            kmsKeyArns: []
        });
        artifact.grantRead(role.role);

        const model = new sagemaker.CfnModel(this, 'Model', {
            executionRoleArn: role.role.roleArn,
            primaryContainer: {
                image: props.image,
                modelDataUrl: artifact.s3ObjectUrl,
                environment: {
                    // one worker: a single copy of SAM in memory
                    SAGEMAKER_MODEL_SERVER_WORKERS: '1',
                    MMS_DEFAULT_WORKERS_PER_MODEL: '1',
                    SAGEMAKER_CONTAINER_LOG_LEVEL: '20'
                }
            }
        });
        model.node.addDependency(role);

        const endpointConfig = new sagemaker.CfnEndpointConfig(this, 'EndpointConfig', {
            productionVariants: [{
                variantName: 'AllTraffic',
                modelName: model.attrModelName,
                serverlessConfig: {
                    memorySizeInMb: props.memorySizeInMb,
                    maxConcurrency: props.maxConcurrency
                }
            }]
        });

        const endpoint = new sagemaker.CfnEndpoint(this, 'Endpoint', {
            endpointName: props.endpointName,
            endpointConfigName: endpointConfig.attrEndpointConfigName
        });

        // AWS::SageMaker::Endpoint only exposes the ARN (Ref); the name is ours.
        this.endpointName = props.endpointName;
        this.endpointArn = endpoint.ref;
    }
}
