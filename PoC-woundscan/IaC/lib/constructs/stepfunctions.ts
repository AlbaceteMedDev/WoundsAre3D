import { Construct } from "constructs";
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import { Duration } from "aws-cdk-lib";

export interface StepFunctionsProps {
    machineName: string;
    timeoutInSeconds: number;
    logGroup: logs.ILogGroup;
    logLevel: sfn.LogLevel;
    step1Lambda: lambda.Function;
    step2Lambda: lambda.Function;
    step3Lambda: lambda.Function;
    step4Lambda: lambda.Function;
    step5Lambda: lambda.Function;
    sessionTable: dynamodb.ITableV2;
    sessionTableKmsKey: kms.IKey;
}

/**
 * Wound-scan workflow (input: {scanId, bucket, prefix, session}).
 *
 *   MarkProcessing -> PREPROCESS -> SEGMENT -> COMPUTE -> GENERATE_DIAGRAMS -> NARRATE -> MarkComplete
 *                         \___________\__________\______________\_______________\--> MarkFailed -> Fail
 *
 * Steps exchange data only through S3; each Lambda gets {scanId, bucket, prefix,
 * retryCount} and its small JSON summary is stored under $.steps.<step>.
 * DynamoDB `status` (attribute; key is `id`) moves PROCESSING -> COMPLETE | FAILED,
 * with `error` holding the failing step's message for GET /scans/{id}/results.
 */
export class StepFunctions extends Construct {
    public readonly stateMachine: sfn.StateMachine;
    constructor(scope: Construct, id: string, props: StepFunctionsProps){
        super(scope, id);

        const key = { id: tasks.DynamoAttributeValue.fromString(sfn.JsonPath.stringAt('$.scanId')) };

        const markProcessing = new tasks.DynamoUpdateItem(this, 'MarkProcessing', {
            table: props.sessionTable,
            key,
            updateExpression: 'SET #s = :s, executionArn = :x, startedAt = :t REMOVE #e',
            expressionAttributeNames: { '#s': 'status', '#e': 'error' },
            expressionAttributeValues: {
                ':s': tasks.DynamoAttributeValue.fromString('PROCESSING'),
                ':x': tasks.DynamoAttributeValue.fromString(sfn.JsonPath.executionId),
                ':t': tasks.DynamoAttributeValue.fromString(sfn.JsonPath.stringAt('$$.Execution.StartTime'))
            },
            resultPath: sfn.JsonPath.DISCARD
        });

        const markComplete = new tasks.DynamoUpdateItem(this, 'MarkComplete', {
            table: props.sessionTable,
            key,
            updateExpression: 'SET #s = :s, completedAt = :t, segmentation = :m, narrationSource = :n',
            expressionAttributeNames: { '#s': 'status' },
            expressionAttributeValues: {
                ':s': tasks.DynamoAttributeValue.fromString('COMPLETE'),
                ':t': tasks.DynamoAttributeValue.fromString(sfn.JsonPath.stringAt('$$.State.EnteredTime')),
                ':m': tasks.DynamoAttributeValue.fromString(sfn.JsonPath.stringAt('$.steps.segment.method')),
                ':n': tasks.DynamoAttributeValue.fromString(sfn.JsonPath.stringAt('$.steps.narrate.source'))
            },
            resultPath: sfn.JsonPath.DISCARD
        });

        // JSONata so the Lambda error JSON can be parsed into a readable message.
        const markFailed = tasks.DynamoUpdateItem.jsonata(this, 'MarkFailed', {
            table: props.sessionTable,
            key: { id: tasks.DynamoAttributeValue.fromString('{% $states.input.scanId %}') },
            updateExpression: 'SET #s = :s, #e = :e, failedStep = :f, failedAt = :t',
            expressionAttributeNames: { '#s': 'status', '#e': 'error' },
            expressionAttributeValues: {
                ':s': tasks.DynamoAttributeValue.fromString('FAILED'),
                ':e': tasks.DynamoAttributeValue.fromString(
                    "{% ($c := $states.input.failure.Cause; $m := ($c and $substring($c, 0, 1) = '{') ? $parse($c).errorMessage : $c; " +
                    "$substring($states.input.failedStep & ' failed: ' & ($m ? $string($m) : $states.input.failure.Error), 0, 1000)) %}"),
                ':f': tasks.DynamoAttributeValue.fromString('{% $states.input.failedStep %}'),
                ':t': tasks.DynamoAttributeValue.fromString('{% $states.context.State.EnteredTime %}')
            },
            outputs: '{% $states.input %}'
        });
        const failed = new sfn.Fail(this, 'ScanFailed', {
            error: 'ScanProcessingFailed',
            causePath: '$.failure.Cause'
        });
        markFailed.next(failed);

        const createStep = (stateId: string, stepName: string, resultKey: string, fn: lambda.Function,
                            retry: { interval: number, maxAttempts: number }) => {
            const step = new tasks.LambdaInvoke(this, stateId, {
                lambdaFunction: fn,
                payload: sfn.TaskInput.fromObject({
                    'scanId.$': '$.scanId',
                    'bucket.$': '$.bucket',
                    'prefix.$': '$.prefix',
                    'retryCount.$': '$$.State.RetryCount'
                }),
                payloadResponseOnly: true,
                resultPath: `$.steps.${resultKey}`,
                retryOnServiceExceptions: true
            });
            // PipelineError = deterministic, user-meaningful failure: do not retry.
            step.addRetry({ errors: ['PipelineError'], maxAttempts: 0 });
            step.addRetry({
                errors: [sfn.Errors.ALL],
                interval: Duration.seconds(retry.interval),
                maxAttempts: retry.maxAttempts,
                backoffRate: 2
            });
            // Record which step failed, then mark the scan FAILED.
            const tag = new sfn.Pass(this, `${stateId}Failed`, {
                parameters: {
                    'scanId.$': '$.scanId',
                    'failedStep': stepName,
                    'failure.$': '$.failure'
                }
            });
            tag.next(markFailed);
            step.addCatch(tag, { errors: [sfn.Errors.ALL], resultPath: '$.failure' });
            return step;
        };

        const step1 = createStep('Preprocess', 'PREPROCESS', 'preprocess', props.step1Lambda, { interval: 3, maxAttempts: 1 });
        // SEGMENT: SageMaker Serverless cold start can take 30-90 s, so retry patiently;
        // on the last attempt (retryCount=2) the Lambda falls back to depth segmentation.
        const step2 = createStep('Segment', 'SEGMENT', 'segment', props.step2Lambda, { interval: 15, maxAttempts: 2 });
        const step3 = createStep('Compute', 'COMPUTE', 'compute', props.step3Lambda, { interval: 3, maxAttempts: 1 });
        const step4 = createStep('GenerateDiagrams', 'GENERATE_DIAGRAMS', 'diagrams', props.step4Lambda, { interval: 3, maxAttempts: 1 });
        const step5 = createStep('Narrate', 'NARRATE', 'narrate', props.step5Lambda, { interval: 5, maxAttempts: 2 });

        markProcessing.addCatch(
            new sfn.Pass(this, 'MarkProcessingFailed', {
                parameters: { 'scanId.$': '$.scanId', 'failedStep': 'START', 'failure.$': '$.failure' }
            }).next(markFailed),
            { errors: [sfn.Errors.ALL], resultPath: '$.failure' });

        const sfnDefinition = markProcessing
            .next(step1)
            .next(step2)
            .next(step3)
            .next(step4)
            .next(step5)
            .next(markComplete);

        this.stateMachine = new sfn.StateMachine(this, id, {
            stateMachineName: props.machineName,
            definitionBody: sfn.DefinitionBody.fromChainable(sfnDefinition),
            timeout: Duration.seconds(props.timeoutInSeconds),
            logs: {
                destination: props.logGroup,
                level: props.logLevel,
                includeExecutionData: true,
            },
        });
        props.sessionTableKmsKey.grantEncryptDecrypt(this.stateMachine);
    }
}
