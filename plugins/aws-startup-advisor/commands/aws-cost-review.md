---
description: Audit AWS spend in this repo's infrastructure and produce a prioritized list of savings opportunities.
argument-hint: "[optional-scope: service, dir, or line item]"
allowed-tools: Read, Grep, Glob, Bash, WebFetch
---

Run a startup-focused AWS cost review of the current repository. Apply the
`aws-cost-optimization` skill (its method and the `references/cost-traps.md`
catalog). Goal: find the biggest, lowest-effort savings and hand back a ranked,
actionable plan — not a lecture.

Scope: if `$ARGUMENTS` is provided, focus the review on that service, directory,
or cost line item. Otherwise review the whole repo.

1. **Detect the IaC.** Look for and read whatever exists:
   - Terraform: `*.tf`, `*.tfvars`
   - AWS CDK: `cdk.json`, `*-stack.ts`, `*-stack.py`
   - CloudFormation / SAM: `template.yaml`, `template.yml`, `samconfig.toml`
   - Serverless Framework: `serverless.yml`
   - Pulumi: `Pulumi.yaml`, `*.pulumi.*`
   - Raw AWS CLI / boto3 usage in scripts
   If none exist, say so and review from the account/architecture the user
   describes. If credentials are configured, you MAY run read-only commands
   (`aws ce get-cost-and-usage`, `describe-*`, `list-*`) to ground findings.

2. **Hunt the traps.** Walk the cost-traps catalog against what you found. Look
   especially for: NAT Gateways without S3/DynamoDB gateway endpoints; cross-AZ
   chatter and internet egress; oversized or idle RDS and Multi-AZ in non-prod
   (Multi-AZ is for HA, not read scaling — and roughly doubles instance cost);
   on-demand compute that could use Compute Savings Plans, Graviton, or Spot;
   `gp2` volumes that should be `gp3`; unattached EBS volumes, stale snapshots,
   idle EIPs; missing S3 lifecycle rules and un-aborted multipart uploads;
   over-provisioned Lambda memory; never-expiring CloudWatch Logs; a load
   balancer fronting a single service; dev/staging left running nights and
   weekends; forgotten resources in unused regions.

3. **Report.** Rank findings **P0/P1/P2** by savings-per-effort. For each:
   **Problem → Impact (rough $ shape / relative magnitude — mark exact figures
   "(verify current pricing)") → Concrete fix** (the exact IaC change or diff,
   e.g. add a VPC S3 gateway endpoint, flip `gp2`→`gp3`, add a lifecycle rule).
   End with a one-line "start here" pick and a note to add AWS Budgets + Cost
   Anomaly Detection so regressions get caught automatically.
