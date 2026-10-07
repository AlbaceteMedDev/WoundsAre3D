import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as kms from 'aws-cdk-lib/aws-kms';
import { EnvironmentConfig } from '../types/environment';
import { S3Bucket } from '../constructs/s3';
import { KMSKey } from '../constructs/kms';

export class BucketStack extends cdk.Stack {
  public readonly assetBucket: s3.IBucket;
  public readonly assetBucketKmsKey: kms.IKey;
  public readonly stepFunctionsBucket: s3.IBucket;
  public readonly stepFunctionsBucketKmsKey: kms.IKey;

  constructor(scope: Construct, id: string, props: EnvironmentConfig) {
    super(scope, id, { env: { account: props.account, region: props.region } })
    cdk.Tags.of(this).add('Workspace', 'IaC/Buckets');
    cdk.Tags.of(this).add('Env', `${props.environment}`);
    cdk.Tags.of(this).add('CDK', "true");

    let identifier = `${props.identifier}-${props.environment}`;

    const assetBucketKMS = new KMSKey(this, 'AssetBucketKms', {
        description: `${identifier} Multi-region key for S3 Assets Bucket.`
    });

    const assetBucket = new S3Bucket(this, 'AssetBucket', {
      bucketNamePrefix: `${identifier}-${props.s3.assetsBucket.name}`,
      bucketNamespace: s3.BucketNamespace.ACCOUNT_REGIONAL,
      versioned: true,
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: assetBucketKMS.kmsKey,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      presignedUrl: props.s3.assetsBucket.presignedUrl,
      corsOrigins: props.s3.assetsBucket.corsOrigins
    });
    
    const stepFunctionsBucketKMS = new KMSKey(this, 'StepFunctionsStateBucketKms', {
        description: `${identifier} Multi-region key for S3 Step Functions State Bucket.`
    });

    const stepFunctionsBucket = new S3Bucket(this, 'StepFunctionsStateBucket', {
      bucketNamePrefix: `${identifier}-${props.s3.stepFunctionsBucket.name}`,
      bucketNamespace: s3.BucketNamespace.ACCOUNT_REGIONAL,
      versioned: true,
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: stepFunctionsBucketKMS.kmsKey,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      presignedUrl: props.s3.stepFunctionsBucket.presignedUrl,
      corsOrigins: props.s3.stepFunctionsBucket.corsOrigins
    });

    this.assetBucket = assetBucket.bucket;
    this.assetBucketKmsKey = assetBucketKMS.kmsKey;
    this.stepFunctionsBucket = stepFunctionsBucket.bucket;
    this.stepFunctionsBucketKmsKey = stepFunctionsBucketKMS.kmsKey;
  }
}