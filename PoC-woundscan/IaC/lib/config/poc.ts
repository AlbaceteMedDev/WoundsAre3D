import { EnvironmentConfig } from '../types/environment';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as workflow from 'aws-cdk-lib/aws-stepfunctions';

export const pocConfig: EnvironmentConfig = {
    account: "962524581373",
    region: "us-east-1",
    environment: "poc",
    identifier: "wound-scan",
    s3: {
        assetsBucket: {
            name: "assets",
            presignedUrl: true
        },
        stepFunctionsBucket: {
            name: "sf-state",
            presignedUrl: false
        }
    },
    dynamoDB: {
        schemaSession: {
            tableName: "session-schema",
            partitionKeyName: "id",
            contributorInsightsSpecification: true
        }
    },
    compute: {
        apiHandlerLambda: {
            functionName: "ApiHandlerLambda",
            runtime: lambda.Runtime.PYTHON_3_13,
            handlerName: "index.handler",
            codePath: "Backend/lambdas/api_handler",
            timeoutInSeconds: 30,
            memorySize: 256,
            layerEnabled: false
        },
        uploadCoordinatorLambda: {
            functionName: "UploadCoordinatorLambda",
            runtime: lambda.Runtime.PYTHON_3_13,
            handlerName: "index.handler",
            codePath: "Backend/lambdas/upload_coordinator",
            timeoutInSeconds: 30,
            memorySize: 256,
            layerEnabled: false
        },
        preprocessLambda: {
            functionName: "PreProcessLambda",
            runtime: lambda.Runtime.PYTHON_3_13,
            handlerName: "index.handler",
            codePath: "Backend/lambdas/step_functions/preprocess",
            layerEnabled: false
        },
        segmentLambda: {
            functionName: "SegmentLambda",
            runtime: lambda.Runtime.PYTHON_3_13,
            handlerName: "index.handler",
            codePath: "Backend/lambdas/step_functions/segment",
            layerEnabled: false,
            environment: {
                "SAGEMAKER_ENDPOINT_ARN": "arn:aws:sagemaker:us-east-1:962524581373:endpoint/wound-scan-poc-sam-endpoint"
            }
        },
        computeLambda: {
            functionName: "ComputeLambda",
            runtime: lambda.Runtime.PYTHON_3_13,
            handlerName: "index.handler",
            codePath: "Backend/lambdas/step_functions/compute",
            layerEnabled: false
        },
        generateDiagramsLambda: {
            functionName: "GenerateDiagramsLambda",
            runtime: lambda.Runtime.PYTHON_3_13,
            handlerName: "index.handler",
            codePath: "Backend/lambdas/step_functions/generate_diagrams",
            layerEnabled: false
        },
        narrateLambda: {
            functionName: "NarrateLambda",
            runtime: lambda.Runtime.PYTHON_3_13,
            handlerName: "index.handler",
            codePath: "Backend/lambdas/step_functions/narrate",
            layerEnabled: false
        }
    },
    sqs: {
        assetsQueue: {
            name: "assets",
            visibilityTimeoutSeconds: 180,
            dlq: {
                visibilityTimeoutSeconds: 180,
                maxReceiveCount: 3
            }
        }
    },
    stepFunctions: {
        stateMachineName: "workflow",
        stateMachineTimeoutInSeconds: 300,
        stateMachineLogLevel: workflow.LogLevel.ALL,
        logRetentionDays: 30,
        sageMaker: {
            jobName: "model-training",
            logRetentionDays: 30
        }
    }
}