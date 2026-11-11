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
        // Pipeline steps: implementation in Backend/lambdas/step_functions/shared/woundlib
        // (shipped in the pipeline-deps layer with numpy + Pillow).
        preprocessLambda: {
            functionName: "PreProcessLambda",
            runtime: lambda.Runtime.PYTHON_3_13,
            handlerName: "index.handler",
            codePath: "Backend/lambdas/step_functions/preprocess",
            timeoutInSeconds: 120,
            memorySize: 2048,          // decodes five 3840x2160 JPEGs
            layerEnabled: false,
            pipelineLayer: true
        },
        segmentLambda: {
            functionName: "SegmentLambda",
            runtime: lambda.Runtime.PYTHON_3_13,
            handlerName: "index.handler",
            codePath: "Backend/lambdas/step_functions/segment",
            timeoutInSeconds: 180,     // SAM serverless cold start can take 30-90 s
            memorySize: 2048,
            layerEnabled: false,
            pipelineLayer: true
            // SAGEMAKER_ENDPOINT_NAME / _ARN are injected from AIMLStack
        },
        computeLambda: {
            functionName: "ComputeLambda",
            runtime: lambda.Runtime.PYTHON_3_13,
            handlerName: "index.handler",
            codePath: "Backend/lambdas/step_functions/compute",
            timeoutInSeconds: 120,
            memorySize: 2048,
            layerEnabled: false,
            pipelineLayer: true
        },
        generateDiagramsLambda: {
            functionName: "GenerateDiagramsLambda",
            runtime: lambda.Runtime.PYTHON_3_13,
            handlerName: "index.handler",
            codePath: "Backend/lambdas/step_functions/generate_diagrams",
            timeoutInSeconds: 60,
            memorySize: 1024,
            layerEnabled: false,
            pipelineLayer: true
        },
        narrateLambda: {
            functionName: "NarrateLambda",
            runtime: lambda.Runtime.PYTHON_3_13,
            handlerName: "index.handler",
            codePath: "Backend/lambdas/step_functions/narrate",
            timeoutInSeconds: 180,     // several Bedrock attempts + guardrail checks
            memorySize: 512,
            layerEnabled: false,
            pipelineLayer: true
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
        stateMachineTimeoutInSeconds: 900,   // SAM cold start + retries + Bedrock narration
        stateMachineLogLevel: workflow.LogLevel.ALL,
        logRetentionDays: 30,
        sageMaker: {
            jobName: "model-training",
            logRetentionDays: 30
        }
    },
    ai: {
        sam: {
            // Same endpoint name as the deleted real-time GPU endpoint, now Serverless (CPU).
            endpointName: "sam-endpoint",
            image: "763104351884.dkr.ecr.us-east-1.amazonaws.com/huggingface-pytorch-inference:2.6.0-transformers4.51.3-cpu-py312-ubuntu22.04",
            modelArtifactPath: "Backend/sagemaker/sam/build/model.tar.gz",
            logGroupName: "/aws/sagemaker/Endpoints/wound-scan-poc-sam-endpoint",
            memorySizeInMb: 6144,      // max for Serverless; more memory = more vCPU = faster SAM
            maxConcurrency: 2          // caps spend; POC volume is a few scans a day
        },
        narration: {
            // Claude is not available on this account (Marketplace payment instrument).
            // gpt-oss-120b passes the v2 guardrail; Llama 3.3 70B is the fallback.
            modelIds: "openai.gpt-oss-120b-1:0,us.meta.llama3-3-70b-instruct-v1:0"
        }
    }
}