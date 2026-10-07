import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as kms from 'aws-cdk-lib/aws-kms';
import { PresignedBucketConfig } from '../types/environment';

export interface S3BucketProps {
  bucketNamePrefix: string;
  bucketNamespace: s3.BucketNamespace;
  presignedUrl: boolean;
  corsOrigins?: PresignedBucketConfig[];
  versioned?: boolean;
  encryption?: s3.BucketEncryption;
  encryptionKey?: kms.Key;
  removalPolicy?: cdk.RemovalPolicy;
  autoDeleteObjects?: boolean;
}

export class S3Bucket extends Construct {
  public readonly bucket: s3.Bucket;

  constructor(scope: Construct, id: string, props: S3BucketProps) {
    super(scope, id);

    this.bucket = new s3.Bucket(this, id, {
      bucketNamePrefix: props.bucketNamePrefix,
      bucketNamespace: props.bucketNamespace,
      versioned: props.versioned,
      encryption: props.encryption,
      encryptionKey: props.encryptionKey,
      removalPolicy: props.removalPolicy,
      autoDeleteObjects: props.autoDeleteObjects
    });

    if (props.presignedUrl){
        let allowedOrigins: string[] = [];
        
        for (let origin of props.corsOrigins ?? []){
            allowedOrigins.push(`https://${origin.subdomain}.${origin.hostedZone}`);
        }
        
        this.bucket.addCorsRule({
            allowedMethods: [s3.HttpMethods.PUT],
            allowedOrigins: allowedOrigins.length > 0 ? allowedOrigins : ["*"],
            allowedHeaders: ["*"],
            exposedHeaders: ["ETag"],
            maxAge: 3000
        })
    }
  }
  
}