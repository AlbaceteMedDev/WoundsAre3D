import { Construct } from "constructs";
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import { Duration } from "aws-cdk-lib";

export interface StepFunctionsProps {
    machineName: string;
    timeoutInSeconds: number;
    logGroup: logs.ILogGroup;
    logLevel: sfn.LogLevel;
    step1Lambda: lambda.Function;
    step2Lambda: lambda.Function;
    step3Lambda: lambda.Function;
    step4Lambda: lambda.Function;
    step5Lambda: lambda.Function;
}

export class StepFunctions extends Construct {
    public readonly stateMachine: sfn.StateMachine;
    constructor(scope: Construct, id: string, props: StepFunctionsProps){
        super(scope, id);
        const createStep = (id: string, lambdaFunction: lambda.Function) => {
            return new tasks.LambdaInvoke(this, id, {
                lambdaFunction: lambdaFunction
            });
        }
        const step1 = createStep('Preprocess', props.step1Lambda);
        const step2 = createStep('Segment', props.step2Lambda);
        const step3 = createStep('Compute', props.step3Lambda);
        const step4 = createStep('GenerateDiagrams', props.step4Lambda);
        const step5 = createStep('Narrate', props.step5Lambda);
        
        const sfnDefinition = step1
        .next(step2)
        .next(step3)
        .next(step4)
        .next(step5)

        this.stateMachine = new sfn.StateMachine(this, id, {
            stateMachineName: props.machineName,
            definitionBody: sfn.DefinitionBody.fromChainable(sfnDefinition),
            timeout: Duration.seconds(props.timeoutInSeconds),
            logs: {
                destination: props.logGroup,
                level: props.logLevel,
                includeExecutionData: true,
            },
        })
    }
}