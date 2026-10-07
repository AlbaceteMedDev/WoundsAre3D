import * as cdk from 'aws-cdk-lib/core';
import { Construct } from 'constructs';
import { EnvironmentConfig } from '../types/environment';
import { DynamoDBTable } from '../constructs/dynamodb';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as kms from 'aws-cdk-lib/aws-kms';
import { KMSKey } from '../constructs/kms'

export class DBStack extends cdk.Stack {
    public readonly sessionTable: dynamodb.ITableV2;
    public readonly dynamoKmsKey: kms.IKey;

    constructor(scope: Construct, id: string, props: EnvironmentConfig){
        super(scope, id, { env: { account: props.account, region: props.region } })
        cdk.Tags.of(this).add('Workspace', 'IaC/Data');
        cdk.Tags.of(this).add('Env', `${props.environment}`);
        cdk.Tags.of(this).add('CDK', "true");

        let identifier = `${props.identifier}-${props.environment}`;

        const dynamoDBKMS = new KMSKey(this, 'DynamoDbKms', {
            description: `${identifier} Multi-region key for DynamoDB Tables.`
        });
        
        const sessionSchemaTable = new DynamoDBTable(this, 'SessionSchema', {
            tableName: `${identifier}-${props.dynamoDB.schemaSession.tableName}`,
            partitionKeyName: props.dynamoDB.schemaSession.partitionKeyName,
            partitionKeyType: dynamodb.AttributeType.STRING,
            sortKeyName: props.dynamoDB.schemaSession.sortKeyName,
            sortKeyType: dynamodb.AttributeType.STRING,
            contributorInsightsSpecification: props.dynamoDB.schemaSession.contributorInsightsSpecification,
            encryptionKey: dynamoDBKMS.kmsKey
        })

        this.sessionTable = sessionSchemaTable.dynamoDBTable;
        this.dynamoKmsKey = dynamoDBKMS.kmsKey;
    }
}