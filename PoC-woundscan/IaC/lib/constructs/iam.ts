import { Construct } from 'constructs';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';

// =============== LAMBDA ROLE ===============

export interface LambdaExecutionRoleProps {
    identifier: string;
    logGroup: logs.ILogGroup;
    stepFunctionArns?: string[];
    sageMakerEndpointArns?: string[];
    bedrockIntegration?: boolean;
}

export class LambdaExecutionRole extends Construct {
    public readonly role: iam.Role;

    constructor(scope: Construct, id: string, props: LambdaExecutionRoleProps) {
        super(scope, id);

        this.role = new iam.Role(this, 'Role', {
            roleName: `${props.identifier}-lambda-execution-role`,
            assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
            description: `Lambda execution role for ${props.identifier}`
        });

        this.role.addToPolicy(new iam.PolicyStatement({
            sid: 'CloudWatchLogs',
            actions: ['logs:CreateLogStream', 'logs:PutLogEvents'],
            resources: [props.logGroup.logGroupArn, `${props.logGroup.logGroupArn}:*`]
        }));

        if (props.stepFunctionArns && props.stepFunctionArns.length > 0) {
            this.role.addToPolicy(new iam.PolicyStatement({
                sid: 'StepFunctionsInvoke',
                actions: ['states:StartExecution', 'states:DescribeExecution'],
                resources: props.stepFunctionArns
            }));
        }

        if (props.sageMakerEndpointArns && props.sageMakerEndpointArns.length > 0) {
            this.role.addToPolicy(new iam.PolicyStatement({
                sid: 'SageMakerInvoke',
                actions: ['sagemaker:InvokeEndpoint'],
                resources: props.sageMakerEndpointArns
            }));
        }

        if (props.bedrockIntegration) {
            this.role.addToPolicy(new iam.PolicyStatement({
                sid: 'BedrockInvoke',
                actions: ['bedrock:InvokeModel'],
                resources: ['*']
            }));
            this.role.addToPolicy(new iam.PolicyStatement({
                sid: 'BedrockGuardrail',
                actions: ['bedrock:ApplyGuardrail'],
                resources: ['*']
            }));
        }
    }
}

// =============== STEP FUNCTIONS ROLE ===============

export interface StepFunctionsExecutionRoleProps {
    identifier: string;
    logGroup: logs.ILogGroup;
    lambdaArns: string[];
    s3BucketArns?: string[];
    dynamoTableArns?: string[];
    kmsKeyArns?: string[];
    sageMakerEndpointArns?: string[];
}

export class StepFunctionsExecutionRole extends Construct {
    public readonly role: iam.Role;

    constructor(scope: Construct, id: string, props: StepFunctionsExecutionRoleProps) {
        super(scope, id);

        this.role = new iam.Role(this, 'Role', {
            roleName: `${props.identifier}-sfn-execution-role`,
            assumedBy: new iam.ServicePrincipal('states.amazonaws.com'),
            description: `Step Functions execution role for ${props.identifier}`
        });

        // CloudWatch Logs management actions do not support resource-level permissions
        this.role.addToPolicy(new iam.PolicyStatement({
            sid: 'CloudWatchLogsDelivery',
            actions: [
                'logs:CreateLogDelivery',
                'logs:GetLogDelivery',
                'logs:UpdateLogDelivery',
                'logs:DeleteLogDelivery',
                'logs:ListLogDeliveries',
                'logs:PutResourcePolicy',
                'logs:DescribeResourcePolicies',
                'logs:DescribeLogGroups'
            ],
            resources: ['*']
        }));

        this.role.addToPolicy(new iam.PolicyStatement({
            sid: 'CloudWatchLogsPut',
            actions: ['logs:PutLogEvents'],
            resources: [props.logGroup.logGroupArn, `${props.logGroup.logGroupArn}:*`]
        }));

        if (props.lambdaArns.length > 0) {
            this.role.addToPolicy(new iam.PolicyStatement({
                sid: 'LambdaInvoke',
                actions: ['lambda:InvokeFunction'],
                resources: props.lambdaArns
            }));
        }

        if (props.sageMakerEndpointArns && props.sageMakerEndpointArns.length > 0) {
            this.role.addToPolicy(new iam.PolicyStatement({
                sid: 'SageMakerInvoke',
                actions: ['sagemaker:InvokeEndpoint'],
                resources: props.sageMakerEndpointArns
            }));
        }

        if (props.s3BucketArns && props.s3BucketArns.length > 0) {
            this.role.addToPolicy(new iam.PolicyStatement({
                sid: 'S3BucketList',
                actions: ['s3:ListBucket'],
                resources: props.s3BucketArns
            }));
            this.role.addToPolicy(new iam.PolicyStatement({
                sid: 'S3ObjectAccess',
                actions: ['s3:GetObject', 's3:PutObject'],
                resources: props.s3BucketArns.map(arn => `${arn}/*`)
            }));
        }

        if (props.dynamoTableArns && props.dynamoTableArns.length > 0) {
            this.role.addToPolicy(new iam.PolicyStatement({
                sid: 'DynamoDBAccess',
                actions: [
                    'dynamodb:GetItem',
                    'dynamodb:PutItem',
                    'dynamodb:UpdateItem',
                    'dynamodb:Query'
                ],
                resources: props.dynamoTableArns
            }));
        }

        if (props.kmsKeyArns && props.kmsKeyArns.length > 0) {
            this.role.addToPolicy(new iam.PolicyStatement({
                sid: 'KMSAccess',
                actions: ['kms:Decrypt', 'kms:GenerateDataKey'],
                resources: props.kmsKeyArns
            }));
        }
    }
}

// =============== SAGEMAKER ROLE ===============

export interface SageMakerExecutionRoleProps {
    identifier: string;
    logGroup: logs.ILogGroup;
    s3BucketArns: string[];
    kmsKeyArns: string[];
}

export class SageMakerExecutionRole extends Construct {
    public readonly role: iam.Role;

    constructor(scope: Construct, id: string, props: SageMakerExecutionRoleProps) {
        super(scope, id);

        this.role = new iam.Role(this, 'Role', {
            roleName: `${props.identifier}-sagemaker-execution-role`,
            assumedBy: new iam.ServicePrincipal('sagemaker.amazonaws.com'),
            description: `SageMaker execution role for ${props.identifier}`
        });

        this.role.addToPolicy(new iam.PolicyStatement({
            sid: 'CloudWatchLogs',
            actions: [
                'logs:CreateLogStream',
                'logs:PutLogEvents',
                'logs:DescribeLogStreams'
            ],
            resources: [props.logGroup.logGroupArn, `${props.logGroup.logGroupArn}:*`]
        }));

        if (props.s3BucketArns.length > 0) {
            this.role.addToPolicy(new iam.PolicyStatement({
                sid: 'S3BucketList',
                actions: ['s3:ListBucket'],
                resources: props.s3BucketArns
            }));
            this.role.addToPolicy(new iam.PolicyStatement({
                sid: 'S3ObjectAccess',
                actions: ['s3:GetObject', 's3:PutObject'],
                resources: props.s3BucketArns.map(arn => `${arn}/*`)
            }));
        }

        if (props.kmsKeyArns.length > 0) {
            this.role.addToPolicy(new iam.PolicyStatement({
                sid: 'KMSAccess',
                actions: ['kms:Decrypt', 'kms:GenerateDataKey', 'kms:Encrypt'],
                resources: props.kmsKeyArns
            }));
        }

        // ecr:GetAuthorizationToken does not support resource-level permissions
        this.role.addToPolicy(new iam.PolicyStatement({
            sid: 'ECRAuth',
            actions: ['ecr:GetAuthorizationToken'],
            resources: ['*']
        }));

        this.role.addToPolicy(new iam.PolicyStatement({
            sid: 'ECRImagePull',
            actions: [
                'ecr:GetDownloadUrlForLayer',
                'ecr:BatchGetImage',
                'ecr:BatchCheckLayerAvailability'
            ],
            resources: [`arn:aws:ecr:*:*:repository/*`]
        }));
    }
}
