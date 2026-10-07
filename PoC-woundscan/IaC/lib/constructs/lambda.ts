import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Duration } from 'aws-cdk-lib';

export interface LambdaProps{
    functionName: string;
    runtime: lambda.Runtime;
    handler: string;
    code: lambda.Code;
    role: iam.Role;
    logGroup?: logs.ILogGroup;
    timeout?: Duration;
    memorySize?: number;
    environment?: Record<string,string>;
    layerEnabled: boolean;
    layerCode?: lambda.Code;
    layerPath?: string;
    layerName?: string;
    layerRuntimes?: lambda.Runtime[];
    layerDescription?: string;
}

export class LambdaFunction extends Construct {
    public readonly lambda: lambda.Function;
    
    constructor(scope: Construct, id: string, props: LambdaProps){
        super(scope, id)
        if (props.layerEnabled) {
            const layer = new lambda.LayerVersion(this, `${id}-layer`, {
                code: props.layerCode!,
                compatibleRuntimes: props.layerRuntimes,
                description: props.layerDescription
            });
            this.lambda = new lambda.Function(this, id, {
                functionName: props.functionName,
                runtime: props.runtime,
                handler: props.handler,
                code: props.code,
                timeout: (props.timeout) ? props.timeout : Duration.seconds(30),
                memorySize: (props.memorySize) ? props.memorySize : 128,
                role: props.role,
                logGroup: props.logGroup,
                layers: [layer],
                environment: (props.environment) ? props.environment : {}
            });

        } else {
            this.lambda = new lambda.Function(this, id, {
                functionName: props.functionName,
                runtime: props.runtime,
                handler: props.handler,
                code: props.code,
                timeout: (props.timeout) ? props.timeout : Duration.seconds(30),
                memorySize: (props.memorySize) ? props.memorySize : 128,
                role: props.role,
                logGroup: props.logGroup,
                environment: (props.environment) ? props.environment : {}
            });
        }

    }
}