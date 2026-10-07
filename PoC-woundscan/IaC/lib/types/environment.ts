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
}