import { Construct } from 'constructs';
import * as bedrock from 'aws-cdk-lib/aws-bedrock';

export interface BedrockGuardrailProps {
    name: string;
}

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
                topicsConfig: [
                    {
                        name: 'MedicalDiagnosis',
                        definition: 'Any statement that diagnoses a medical condition, names a disease, or classifies wounds by medical criteria.',
                        examples: [
                            'This appears to be a diabetic ulcer.',
                            'The wound shows signs of infection.',
                            'This is consistent with a venous leg ulcer.',
                        ],
                        type: 'DENY',
                    },
                    {
                        name: 'WoundStaging',
                        definition: 'Classification of wounds using any staging system such as NPUAP/EPUAP pressure injury stages, Wagner grades, or similar medical staging.',
                        examples: [
                            'This is a Stage III pressure injury.',
                            'Wagner Grade 2 ulcer.',
                            'Is this a Stage III wound?',
                        ],
                        type: 'DENY',
                    },
                    {
                        name: 'TreatmentRecommendation',
                        definition: 'Any recommendation for medical treatment, dressing type, wound care procedure, medication, or clinical intervention.',
                        examples: [
                            'Apply a hydrocolloid dressing.',
                            'This wound requires surgical debridement.',
                            'Consider starting antibiotic therapy.',
                        ],
                        type: 'DENY',
                    },
                    {
                        name: 'Prognosis',
                        definition: 'Any prediction about wound healing trajectory, recovery timeline, infection risk, or clinical outcomes.',
                        examples: [
                            'This wound should heal within two weeks.',
                            'There is a high risk of infection.',
                            'Healing is unlikely without intervention.',
                        ],
                        type: 'DENY',
                    },
                ],
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
        const guardrailVersion = new bedrock.CfnGuardrailVersion(this, `${id}Version`, {
            guardrailIdentifier: guardrail.attrGuardrailId,
            description: 'Initial production version',
        });

        this.guardRail = guardrail;
        this.guardrailVersion = guardrailVersion.attrVersion;
    }
}
