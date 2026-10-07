import * as cdk from 'aws-cdk-lib/core';
import { Construct } from "constructs";
import { EnvironmentConfig } from '../types/environment';
import { BedrockGuardrail } from '../constructs/bedrock';

export class AIStack extends cdk.Stack {
    public readonly guardrailId: string;
    public readonly guardrailArn: string;
    public readonly guardrailVersion: string;

    constructor(scope: Construct, id: string, props: EnvironmentConfig){
        super(scope, id, { env: { account: props.account, region: props.region }})
        cdk.Tags.of(this).add('Workspace', 'IaC/AI-ML');
        cdk.Tags.of(this).add('Env', `${props.environment}`);
        cdk.Tags.of(this).add('CDK', "true");

        const identifier = `${props.identifier}-${props.environment}`;

        const bedrockGuardRail = new BedrockGuardrail(this, 'NarrateGuardRail', {
            name: `${identifier}-narrate-guardrail`
        });

        this.guardrailId = bedrockGuardRail.guardRail.attrGuardrailId;
        this.guardrailArn = bedrockGuardRail.guardRail.attrGuardrailArn;
        this.guardrailVersion = bedrockGuardRail.guardrailVersion;
    }
}