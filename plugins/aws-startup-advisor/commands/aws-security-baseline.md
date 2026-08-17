---
description: Audit this repo's AWS setup against the startup security baseline and report gaps by severity.
argument-hint: "[optional-scope: identity, network, data, etc.]"
allowed-tools: Read, Grep, Glob, Bash, WebFetch
---

Audit the current repository against a pragmatic AWS security baseline and report
the gaps. Apply the `aws-security-baseline` skill (its priority order and the
`references/security-checklist.md`). Target a baseline a tiny team can actually
reach — prioritize what moves real risk over box-checking. Note that compliance
(SOC 2 / HIPAA) builds ON this baseline; it doesn't replace it.

Scope: if `$ARGUMENTS` is provided, focus on that area (e.g. identity, network,
data, secrets). Otherwise cover the whole baseline.

1. **Detect the IaC.** Read whatever exists: Terraform (`*.tf`), AWS CDK
   (`cdk.json`, `*-stack.ts/py`), CloudFormation/SAM (`template.yaml`,
   `serverless.yml`), Pulumi, or raw AWS CLI/boto usage. If none exist, assess
   from the described account. If read-only creds exist you MAY run
   `describe-*`/`list-*`/`get-*` to confirm posture.

2. **Grep for the classic gaps,** in priority order (identity → guardrails →
   data → network → detection):
   - **Network:** `0.0.0.0/0` on security-group ingress (especially 22/3306/5432),
     publicly exposed databases.
   - **Data:** public S3 buckets/ACLs, missing encryption (note S3 is SSE-S3
     encrypted by default since Jan 2023; check KMS where required), no EBS
     default encryption.
   - **Identity:** wildcard IAM actions/resources (`"Action": "*"`,
     `"Resource": "*"`), long-lived access keys instead of IAM roles, root-user
     day-to-day use, missing MFA.
   - **Secrets:** hardcoded keys/passwords/tokens in code or `*.tf(vars)`; should
     live in Secrets Manager or SSM Parameter Store.
   - **Detection:** is CloudTrail (org trail), GuardDuty, Security Hub, and AWS
     Config enabled?

3. **Report.** Rank findings by severity **P0/P1/P2** (P0 = internet-exposed
   data, credentials in git, or root without MFA). For each: **Problem → Impact
   (what an attacker gains) → Concrete fix** (the exact IaC change or the AWS tool
   to turn on — CloudTrail, GuardDuty, Config, Security Hub, IAM Identity Center,
   Secrets Manager/SSM, KMS). Lead with the P0s.
