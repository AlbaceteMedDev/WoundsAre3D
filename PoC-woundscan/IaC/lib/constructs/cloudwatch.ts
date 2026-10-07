import { Construct } from 'constructs';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as cdk from 'aws-cdk-lib/core';

export interface CloudWatchLogGroupsProps {
    logGroupResource: string;
    logGroupName: string;
    retentionDays?: logs.RetentionDays;
}

export class CloudWatchLogGroups extends Construct {
    public readonly logGroup: logs.LogGroup;

    constructor(scope: Construct, id: string, props: CloudWatchLogGroupsProps) {
        super(scope, id);

        const retention = props.retentionDays ?? logs.RetentionDays.ONE_MONTH;

        this.logGroup = new logs.LogGroup(this, id, {
            logGroupName: `/aws/${props.logGroupResource}/${props.logGroupName}`,
            retention,
            removalPolicy: cdk.RemovalPolicy.DESTROY
        });
    }
}
