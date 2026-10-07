import { Construct } from "constructs";
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as kms from 'aws-cdk-lib/aws-kms';

export interface DynamoTableProps {
    tableName: string;
    partitionKeyName: string;
    partitionKeyType: dynamodb.AttributeType;
    sortKeyName?: string;
    sortKeyType?: dynamodb.AttributeType;
    contributorInsightsSpecification: boolean;
    encryptionKey?: kms.Key;
}

export class DynamoDBTable extends Construct{
    public readonly dynamoDBTable: dynamodb.TableV2;
    constructor(scope: Construct, id: string, props: DynamoTableProps) {
        super(scope, id);
        this.dynamoDBTable = new dynamodb.TableV2(this, id, {
            tableName: props.tableName,
            partitionKey: { name: props.partitionKeyName, type: props.partitionKeyType },
            sortKey: props.sortKeyName && props.sortKeyType
                ? { name: props.sortKeyName, type: props.sortKeyType }
                : undefined,
            contributorInsightsSpecification: {
                enabled: props.contributorInsightsSpecification
            },
            encryption: props.encryptionKey
                ? dynamodb.TableEncryptionV2.customerManagedKey(props.encryptionKey)
                : dynamodb.TableEncryptionV2.dynamoOwnedKey()
        });
    }
}