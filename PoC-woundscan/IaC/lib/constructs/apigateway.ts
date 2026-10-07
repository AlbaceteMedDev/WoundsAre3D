import * as apigateway from 'aws-cdk-lib/aws-apigatewayv2';
import { Construct } from 'constructs';
import { HttpLambdaIntegration } from 'aws-cdk-lib/aws-apigatewayv2-integrations';


export interface ApiGatewayProps {
    apiName: string;
    apiDescription: string;
}

export class ApiGateway extends Construct {
    public readonly apiGateway: apigateway.HttpApi;

    constructor(scope: Construct, id: string, props: ApiGatewayProps) {
        super(scope, id);
        
        this.apiGateway = new apigateway.HttpApi(this, 'HttpApi', {
            apiName: props.apiName,
            description: props.apiDescription,
            corsPreflight: {
                allowOrigins: ["*"],
                allowMethods: [apigateway.CorsHttpMethod.ANY],
                allowHeaders: ["authorization", "content-type"]
            }
        });
    }
}