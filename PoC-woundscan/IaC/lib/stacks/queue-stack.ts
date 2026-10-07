import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import { EnvironmentConfig } from '../types/environment';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import { SQSQueue } from '../constructs/sqs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';

export interface QueueStackProps extends EnvironmentConfig {
    assetBucket: s3.IBucket;
    assetBucketKmsKey: kms.IKey;
}

export class QueueStack extends cdk.Stack {
    public readonly assetsQueue: sqs.IQueue;

    constructor(scope: Construct, id: string, props: QueueStackProps){
        super(scope, id, { env: { account: props.account, region: props.region } });
        cdk.Tags.of(this).add('Workspace', 'IaC/Queue');
        cdk.Tags.of(this).add('Env', props.environment);
        cdk.Tags.of(this).add('CDK', 'true');

        const identifier = `${props.identifier}-${props.environment}`;

        const assetsQueue = new SQSQueue(this, 'AssetsQueue', {
            queueName: `${identifier}-${props.sqs.assetsQueue.name}-sqs`,
            visibilityTimeOut: props.sqs.assetsQueue.visibilityTimeoutSeconds,
            dlqVisibilityTimeOut: props.sqs.assetsQueue.dlq.visibilityTimeoutSeconds,
            dlqMaxReeceiveCount: props.sqs.assetsQueue.dlq.maxReceiveCount
        })

        // Import the bucket as a local reference so CDK uses a custom resource
        // (BucketNotificationsHandler) in *this* stack instead of embedding the
        // SQS ARN into BucketStack's CloudFormation template — which would
        // create a cyclic cross-stack dependency.
        const assetBucketRef = s3.Bucket.fromBucketAttributes(this, 'AssetBucketRef', {
            bucketArn: props.assetBucket.bucketArn,
            encryptionKey: props.assetBucketKmsKey,
        });
        assetBucketRef.addEventNotification(s3.EventType.OBJECT_CREATED, new s3n.SqsDestination(assetsQueue.sqs));

        this.assetsQueue = assetsQueue.sqs;
    }
}