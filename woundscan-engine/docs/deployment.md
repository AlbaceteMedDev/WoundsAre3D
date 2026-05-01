# Deployment

Production deployment is on AWS HIPAA-eligible services. This document
describes the target infrastructure; the actual Terraform lives in
`infrastructure/terraform/`.

## Topology

```
                       Internet
                          │
                     ┌────▼────┐
                     │   WAF   │
                     └────┬────┘
                          │
                ┌─────────▼──────────┐
                │ ALB (TLS 1.3 only) │
                └─────────┬──────────┘
                          │
              ┌───────────▼────────────┐
              │   ECS Fargate Service  │  (1-10 tasks, autoscaling)
              │      woundscan-api     │
              └─┬──────────┬───────┬───┘
                │          │       │
       ┌────────▼─┐  ┌─────▼────┐ ┌▼──────────┐
       │   RDS    │  │  Redis   │ │    S3     │
       │ Postgres │  │ ElastCache│ │  bucket   │
       │ (encryp- │  │          │ │ (Object   │
       │  tion at │  │          │ │  lock,    │
       │   rest)  │  │          │ │ versioned)│
       └──────────┘  └──────────┘ └───────────┘
```

## Pre-deployment checklist

- [ ] BAA signed with AWS
- [ ] Designated AWS account (no PHI in shared/dev account)
- [ ] CloudTrail enabled with log integrity validation
- [ ] GuardDuty enabled
- [ ] Security Hub enabled with HIPAA controls
- [ ] Secrets Manager populated with: DB password, JWT signing key, TOTP master, S3 credentials
- [ ] Route53 hosted zone for woundscan domain
- [ ] ACM certificate validated for the API hostname
- [ ] WAF rules attached to the ALB

## ECS Fargate

Task definition:
- Image: `woundscan-engine:<git-sha>` (built from `Dockerfile`)
- CPU: 2048 (2 vCPU)
- Memory: 4096 MiB
- Container ports: 8000 (API), 9090 (metrics)
- Health check: `/healthz`
- Log driver: `awslogs` to a HIPAA-compliant log group
- Task role: read access to specific S3 bucket, RDS, Secrets Manager
- Execution role: ECR image pull + log writes

Environment variables (loaded from Secrets Manager):
- `WS_DB_HOST`, `WS_DB_USER`, `WS_DB_PASSWORD`
- `WS_S3_BUCKET`, `WS_S3_REGION`
- `WS_JWT_SIGNING_KEY`
- `WS_CELERY_BROKER`, `WS_CELERY_BACKEND`

Autoscaling: target 70% average CPU, scale 1-10.

## Worker

Same image, started with `woundscan-worker` entrypoint. ECS service with
1-3 tasks for async fusion jobs.

## RDS Postgres

- Engine: Postgres 15
- Storage: 100 GB GP3 with auto-scaling to 1 TB
- Encryption at rest: AES-256, KMS CMK with rotation
- Backups: 7-day retention, point-in-time recovery
- Multi-AZ for production
- Parameter group enables `pg_stat_statements`, `pgaudit`
- Row-level security policies enforced for all PHI tables

Schema migrations via Alembic; auto-applied on deploy via a one-shot ECS
task.

## Redis

ElastiCache Redis 7, encrypted in transit and at rest, used for:
- Session store (15-minute TTL)
- Celery broker + result backend
- Idempotency keys for the upload presign endpoint

## S3

- Encryption at rest: SSE-KMS
- Versioning enabled
- Object lock in governance mode, 6-year default retention
- Lifecycle: transition to Glacier after 30 days, expire after 6 years
- Bucket policy: only the ECS task role can write; no public access

## CloudWatch alarms

- API 5xx rate >1% over 5 min
- Pipeline duration P95 >5s
- Pipeline failures >0 over 1 min
- Quality F-grade rate >25% over 1 hour (operational quality alert)
- DB connection pool exhaustion
- WAF block rate spike (possible attack)

## Backups & DR

- RDS: automated daily backups, 7-day retention
- S3: versioning + cross-region replication to a secondary region
- Recovery procedures documented and rehearsed quarterly
- RTO: 4 hours, RPO: 1 hour

## Access management

- All access via SSO (AWS IAM Identity Center)
- MFA required for AWS Console
- Quarterly access review with deprovisioning workflow
- Emergency break-glass procedure with audit trail

## Penetration testing

Annual third-party penetration test required. Prior reports retained
for regulatory review.
