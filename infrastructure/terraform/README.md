# Infrastructure

Terraform-managed AWS HIPAA-compliant deployment.

```
infrastructure/terraform/
├── modules/
│   ├── vpc/             VPC with private subnets, NAT, flow logs
│   ├── ecs/             ECS Fargate cluster + service for woundscan-api
│   ├── rds/             Postgres 15 with encryption + multi-AZ
│   ├── s3/              Artifact bucket with object lock
│   ├── waf/             WAF rules and ACL
│   └── monitoring/      CloudWatch alarms, GuardDuty, Security Hub
└── environments/
    ├── dev/             Development workspace
    └── prod/            Production workspace
```

## Bootstrapping

```bash
cd environments/dev
terraform init
terraform plan
terraform apply
```

Production deploys are gated on:
- BAA signed
- All `prod` plan output reviewed
- Two-party approval (security + engineering lead)

## State

Terraform state is stored in an S3 backend with DynamoDB lock table.
See `environments/<env>/backend.tf`.

## Secrets

Terraform NEVER reads or writes secrets. Secrets Manager entries are
seeded out-of-band via the AWS CLI:

```bash
aws secretsmanager create-secret \
  --name woundscan/prod/db-password \
  --secret-string "$DB_PASSWORD"
```

Terraform references secret ARNs to attach them to ECS task definitions.
