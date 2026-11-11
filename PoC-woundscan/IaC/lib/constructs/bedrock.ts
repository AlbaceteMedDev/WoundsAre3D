import { Construct } from 'constructs';
import * as cdk from 'aws-cdk-lib/core';
import * as bedrock from 'aws-cdk-lib/aws-bedrock';

export interface BedrockGuardrailProps {
    name: string;
}

// v2 (2026-11-11): topic definitions tightened and moved to the STANDARD tier.
// Measured on 25 factual narrations from 4 models + 12 clinical probes:
//   v1 (CLASSIC, original wording): 19/25 factual narrations wrongly blocked (WoundStaging)
//   v2 (STANDARD, wording below):    0/25 wrongly blocked, 12/12 clinical probes blocked
// The STANDARD tier requires a cross-region guardrail profile.

export class BedrockGuardrail extends Construct {
    public readonly guardrailVersion: string;
    public readonly guardRail: bedrock.CfnGuardrail;

    constructor(scope: Construct, id: string, props: BedrockGuardrailProps) {
        super(scope, id);

        const guardrail = new bedrock.CfnGuardrail(this, id, {
            name: props.name,
            description: 'Blocks medical diagnosis, staging, treatment, and prognosis — narration must report objective measurements only.',
            blockedInputMessaging: 'I can only report objective wound measurements. I cannot provide diagnoses, staging, treatment recommendations, or prognoses.',
            blockedOutputsMessaging: 'I can only report objective wound measurements. I cannot provide diagnoses, staging, treatment recommendations, or prognoses.',

            topicPolicyConfig: {
                topicsTierConfig: { tierName: 'STANDARD' },
                topicsConfig: [
                    {
                        name: 'MedicalDiagnosis',
                        definition: 'Stating or suggesting a medical diagnosis, disease, or cause of a wound, such as calling it an ulcer, burn or infection, or describing signs of infection.',
                        examples: [
                            'This appears to be a diabetic ulcer.',
                            'The wound shows signs of infection.',
                            'This is consistent with a venous leg ulcer.',
                        ],
                        type: 'DENY',
                    },
                    {
                        name: 'WoundStaging',
                        definition: 'Assigning a wound a stage, grade, class or category under a clinical classification system such as NPUAP/EPUAP pressure injury stages or Wagner grades.',
                        examples: [
                            'This is a Stage III pressure injury.',
                            'Wagner Grade 2 ulcer.',
                            'Is this a Stage III wound?',
                            'The depth indicates full-thickness tissue loss.',
                        ],
                        type: 'DENY',
                    },
                    {
                        name: 'TreatmentRecommendation',
                        definition: 'Advising any medical treatment, dressing, wound-care product or procedure, medication, referral, or other clinical intervention.',
                        examples: [
                            'Apply a hydrocolloid dressing.',
                            'This wound requires surgical debridement.',
                            'Consider starting antibiotic therapy.',
                        ],
                        type: 'DENY',
                    },
                    {
                        name: 'Prognosis',
                        definition: 'Predicting healing, recovery time, infection risk, deterioration, or any other future clinical outcome of a wound.',
                        examples: [
                            'This wound should heal within two weeks.',
                            'There is a high risk of infection.',
                            'Healing is unlikely without intervention.',
                        ],
                        type: 'DENY',
                    },
                ],
            },
            crossRegionConfig: {
                guardrailProfileArn: `arn:aws:bedrock:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:guardrail-profile/us.guardrail.v1:0`,
            },

            contentPolicyConfig: {
                filtersConfig: [
                    { type: 'HATE',          inputStrength: 'HIGH', outputStrength: 'HIGH' },
                    { type: 'INSULTS',       inputStrength: 'HIGH', outputStrength: 'HIGH' },
                    { type: 'SEXUAL',        inputStrength: 'HIGH', outputStrength: 'HIGH' },
                    { type: 'VIOLENCE',      inputStrength: 'HIGH', outputStrength: 'HIGH' },
                    { type: 'MISCONDUCT',    inputStrength: 'HIGH', outputStrength: 'HIGH' },
                    // Block prompt injection on input only; output filter set to NONE to avoid false positives
                    { type: 'PROMPT_ATTACK', inputStrength: 'HIGH', outputStrength: 'NONE' },
                ],
            },
        });

        // Publish a versioned snapshot so the Lambda always invokes a stable guardrail.
        // DRAFT is mutable; a version is immutable — safe for production use.
        // Version 1 (original definitions) is kept unchanged for rollback.
        new bedrock.CfnGuardrailVersion(this, `${id}Version`, {
            guardrailIdentifier: guardrail.attrGuardrailId,
            description: 'Initial production version',
        });

        // Version 2 snapshots the updated DRAFT above. Versions are immutable, so a
        // future definition change needs a new CfnGuardrailVersion (v3, ...).
        const guardrailVersion2 = new bedrock.CfnGuardrailVersion(this, `${id}Version2`, {
            guardrailIdentifier: guardrail.attrGuardrailId,
            description: 'v2: tightened topic definitions, STANDARD tier',
        });
        guardrailVersion2.applyRemovalPolicy(cdk.RemovalPolicy.RETAIN);

        this.guardRail = guardrail;
        this.guardrailVersion = guardrailVersion2.attrVersion;
    }
}
