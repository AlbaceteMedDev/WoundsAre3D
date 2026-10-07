import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import { EnvironmentConfig } from '../types/environment';
import { CloudWatchLogGroups } from '../constructs/cloudwatch';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as kms from 'aws-cdk-lib/aws-kms';
import { StepFunctions } from '../constructs/stepfunctions';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';

export interface StepFunctionsProps extends EnvironmentConfig {
    preprocessLambda: lambda.Function;
    segmentLambda: lambda.Function;
    computeLambda: lambda.Function;
    generateDiagramsLambda: lambda.Function;
    narrateLambda: lambda.Function;
    stepFunctionsBucket: s3.IBucket;
    stepFunctionsBucketKmsKey: kms.IKey;
}

export class StepFunctionsStack extends cdk.Stack {
    public readonly stateMachine: sfn.StateMachine;

    constructor(scope: Construct, id: string, props: StepFunctionsProps){
        super(scope, id, { env: { account: props.account, region: props.region } });
        cdk.Tags.of(this).add('Workspace', 'IaC/StepFunctions');
        cdk.Tags.of(this).add('Env', props.environment);
        cdk.Tags.of(this).add('CDK', 'true');

        const identifier = `${props.identifier}-${props.environment}`;
        const workflowName = `${identifier}-${props.stepFunctions.stateMachineName}`;

        // ================== CLOUDWATCH LOG GROUPS ==================
        const stepFunctionsLogGroup = new CloudWatchLogGroups(this, 'StepFunctionsLogGroup', {
            logGroupResource: "states",
            logGroupName: `${identifier}-${props.stepFunctions.stateMachineName}`,
            retentionDays: logs.RetentionDays.ONE_MONTH
        });

        // =================== S3 PERMISSIONS FOR STEP FUNCTIONS LAMBDAS ===================
        const grantS3Roles = (lambda: lambda.Function) => {
            props.stepFunctionsBucket.grantReadWrite(lambda);
            props.stepFunctionsBucketKmsKey.grantDecrypt(lambda);
        };

        grantS3Roles(props.preprocessLambda);
        grantS3Roles(props.segmentLambda);
        grantS3Roles(props.computeLambda);
        grantS3Roles(props.generateDiagramsLambda);
        grantS3Roles(props.narrateLambda);

        const woundScanWorkflow = new StepFunctions(this, "WoundScanWorkflow", {
            machineName: workflowName,
            timeoutInSeconds: props.stepFunctions.stateMachineTimeoutInSeconds,
            logGroup: stepFunctionsLogGroup.logGroup,
            logLevel: props.stepFunctions.stateMachineLogLevel,
            step1Lambda: props.preprocessLambda,
            step2Lambda: props.segmentLambda,
            step3Lambda: props.computeLambda,
            step4Lambda: props.generateDiagramsLambda,
            step5Lambda: props.narrateLambda
        });
        this.stateMachine = woundScanWorkflow.stateMachine;

    }
}