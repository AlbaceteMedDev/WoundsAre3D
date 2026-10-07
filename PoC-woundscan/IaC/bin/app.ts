#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib/core';
import { getConfig } from '../lib/config/config';
import { BucketStack } from '../lib/stacks/bucket-stack';
import { DBStack } from '../lib/stacks/db-stack';
import { ComputeStack } from '../lib/stacks/compute-stack';
import { QueueStack } from '../lib/stacks/queue-stack';
import { StepFunctionsStack } from '../lib/stacks/step-functions-stack';
import { AIStack } from '../lib/stacks/ai-stack';

const app = new cdk.App();

const environment = app.node.tryGetContext('environment');

if (!environment) {
  throw new Error(
    'Environment must be specified. Use -c environment=<ENV>'
  );
}
const config = getConfig(environment);

const bucketStack = new BucketStack(app, 'BucketStack', config);

const dbStack = new DBStack(app, 'DBStack', config);

const queueStack = new QueueStack(app, 'QueueStack', {
  ...config,
  assetBucket: bucketStack.assetBucket,
  assetBucketKmsKey: bucketStack.assetBucketKmsKey
});

const aiStack = new AIStack(app, 'AIMLStack', config);

const computeStack = new ComputeStack(app, 'ComputeStack', {
  ...config,
  assetBucket: bucketStack.assetBucket,
  assetBucketKmsKey: bucketStack.assetBucketKmsKey,
  sessionTable: dbStack.sessionTable,
  sessionTableKmsKey: dbStack.dynamoKmsKey,
  assetQueue: queueStack.assetsQueue,
  bedrockGuardrailID: aiStack.guardrailId,
  bedrockGuardrailVersion: aiStack.guardrailVersion
});

const stepFunctionsStack = new StepFunctionsStack(app, 'StepFunctionsStack', {
  ...config,
  preprocessLambda: computeStack.preprocessLambda,
  segmentLambda: computeStack.segmentLambda,
  computeLambda: computeStack.computeLambda,
  generateDiagramsLambda: computeStack.generateDiagramsLambda,
  narrateLambda: computeStack.narrateLambda,
  stepFunctionsBucket: bucketStack.stepFunctionsBucket,
  stepFunctionsBucketKmsKey: bucketStack.stepFunctionsBucketKmsKey
});