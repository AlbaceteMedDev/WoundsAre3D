import * as path from 'path';
import * as cdk from 'aws-cdk-lib/core';
import { Construct } from "constructs";
import { EnvironmentConfig } from '../types/environment';
import { BedrockGuardrail } from '../constructs/bedrock';
import { SamServerlessEndpoint } from '../constructs/sagemaker';

export class AIStack extends cdk.Stack {
    public readonly guardrailId: string;
    public readonly guardrailArn: string;
    public readonly guardrailVersion: string;
    public readonly samEndpointName: string;
    public readonly samEndpointArn: string;

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

        // ================= SAM ViT-B (SageMaker Serverless) =================
        const sam = new SamServerlessEndpoint(this, 'SamEndpoint', {
            identifier,
            endpointName: `${identifier}-${props.ai.sam.endpointName}`,
            image: props.ai.sam.image,
            modelArtifactFile: path.join(__dirname, '../../../', props.ai.sam.modelArtifactPath),
            logGroupName: props.ai.sam.logGroupName,
            memorySizeInMb: props.ai.sam.memorySizeInMb,
            maxConcurrency: props.ai.sam.maxConcurrency
        });
        this.samEndpointName = sam.endpointName;
        this.samEndpointArn = sam.endpointArn;

        new cdk.CfnOutput(this, 'SamEndpointName', { value: sam.endpointName });
        new cdk.CfnOutput(this, 'GuardrailVersion', { value: this.guardrailVersion });
    }
}
