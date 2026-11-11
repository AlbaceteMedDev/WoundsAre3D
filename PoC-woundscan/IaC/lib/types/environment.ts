import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as workflow from 'aws-cdk-lib/aws-stepfunctions';

// ============== S3 Bucket Configs ===============
export interface PresignedBucketConfig {
    subdomain: string;
    hostedZone: string;
}

export interface BucketConfig {
    name: string;
    presignedUrl: boolean;
    corsOrigins?: PresignedBucketConfig[];
    preloadedFolders?: string[];
}

export interface S3Config {
    assetsBucket: BucketConfig;
    stepFunctionsBucket: BucketConfig;
}
// =========== DynamoDB Table Configs ============
export interface DynamoTableConfig {
    tableName: string;
    partitionKeyName: string;
    sortKeyName?: string;
    contributorInsightsSpecification: boolean;
}

export interface DynamoDBConfig {
    schemaSession: DynamoTableConfig;
}

// ========== Lambda Functions Config ============
export interface LambdaConfig {
    functionName: string;
    runtime: lambda.Runtime;
    handlerName: string;
    codePath: string;
    timeoutInSeconds?: number;
    memorySize?: number;
    layerEnabled: boolean;
    environment?: Record<string,string>
    /** Attach the shared pipeline-deps layer (numpy, Pillow, woundlib). */
    pipelineLayer?: boolean;
}

export interface ComputeConfig {
    apiHandlerLambda: LambdaConfig;
    uploadCoordinatorLambda: LambdaConfig;
    preprocessLambda: LambdaConfig;
    segmentLambda: LambdaConfig;
    computeLambda: LambdaConfig;
    generateDiagramsLambda: LambdaConfig;
    narrateLambda: LambdaConfig;
}
// ================== SQS Config ==================
export interface SQSDLQConfig {
    visibilityTimeoutSeconds: number;
    maxReceiveCount: number;
}
export interface SQSConfig {
    name: string;
    visibilityTimeoutSeconds: number;
    dlq: SQSDLQConfig;
}

export interface QueueConfig {
    assetsQueue: SQSConfig;
}

// =========== Step Functions Config =============
export interface StepFunctionsConfig {
    stateMachineName: string;
    stateMachineTimeoutInSeconds: number;
    stateMachineLogLevel: workflow.LogLevel;
    logRetentionDays: number;
    sageMaker: {
        jobName: string;
        logRetentionDays: number;
    };
}

// ============== AI / ML Config =================
export interface SamEndpointConfig {
    /** Endpoint name suffix: `${identifier}-${environment}-${endpointName}`. */
    endpointName: string;
    /** SageMaker Hugging Face PyTorch inference image (CPU). */
    image: string;
    /** Path (relative to PoC-woundscan/) of the model.tar.gz built by Backend/sagemaker/sam/build_model.py. */
    modelArtifactPath: string;
    /** Existing CloudWatch log group for the endpoint (reused, not created). */
    logGroupName: string;
    memorySizeInMb: number;
    maxConcurrency: number;
}

export interface NarrationConfig {
    /** Comma-separated Bedrock model / inference-profile IDs, tried in order. */
    modelIds: string;
}

export interface AIConfig {
    sam: SamEndpointConfig;
    narration: NarrationConfig;
}

// =============== General Config ================
export interface EnvironmentConfig {
    account: string;
    region: string;
    environment: string;
    identifier: string;

    s3: S3Config;

    dynamoDB: DynamoDBConfig;

    compute: ComputeConfig;

    sqs: QueueConfig;

    stepFunctions: StepFunctionsConfig;

    ai: AIConfig;
}