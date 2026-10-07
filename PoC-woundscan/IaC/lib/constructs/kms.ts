import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import * as kms from 'aws-cdk-lib/aws-kms';

export interface KMSProps {
    description: string;
}
export class KMSKey extends Construct{
    public readonly kmsKey: kms.Key;
    constructor(scope: Construct, id: string, props: KMSProps){
        super(scope, id);

        this.kmsKey = new kms.Key(this, id, {
            description: props.description,
            multiRegion: true
        })
    }
}