import * as cdk from 'aws-cdk-lib/core';
import { Duration } from 'aws-cdk-lib';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import { Construct } from 'constructs';


export interface SQSProps {
    queueName: string;
    visibilityTimeOut: number;
    dlqVisibilityTimeOut: number;
    dlqMaxReeceiveCount: number;
}

export class SQSQueue extends Construct {
    public readonly sqs: sqs.Queue;

    constructor(scope: Construct, id: string, props: SQSProps){
        super(scope, id);
        const sourceQueueArn = cdk.Stack.of(this).formatArn({
            service: 'sqs',
            resource: props.queueName
        });

        const dlq = new sqs.Queue(this, `${id}-DLQ`, {
            queueName: `${props.queueName}-dlq`,
            visibilityTimeout: Duration.seconds(props.visibilityTimeOut),
            redriveAllowPolicy: {
                sourceQueues: [sqs.Queue.fromQueueArn(this, 'SourceQueueRef', sourceQueueArn)],
            }
        });

        this.sqs = new sqs.Queue(this, id, {
            queueName: props.queueName,
            visibilityTimeout: Duration.seconds(props.dlqVisibilityTimeOut),
            deadLetterQueue: {
                maxReceiveCount: props.dlqMaxReeceiveCount,
                queue: dlq
            }
        });
    }
}