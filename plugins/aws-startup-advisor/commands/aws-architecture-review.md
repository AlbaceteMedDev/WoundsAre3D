---
description: Run a startup-weighted Well-Architected review of this repo's AWS setup across the 6 pillars.
argument-hint: "[optional-scope: pillar, service, or dir]"
allowed-tools: Read, Grep, Glob, Bash, WebFetch
---

Run a Well-Architected-lite review of the current repository's AWS architecture.
Apply the `aws-architecture-review` skill (its 6-pillar framework and the
`references/service-selection.md` decision tables). Judge through a startup lens:
Cost Optimization and Operational Excellence (simplicity) dominate early —
flag "best practices" that are premature for a small team.

The 6 pillars: Operational Excellence, Security, Reliability, Performance
Efficiency, Cost Optimization, Sustainability.

Scope: if `$ARGUMENTS` is provided, focus on that pillar, service, or directory.
Otherwise review the whole system.

1. **Detect the IaC.** Read whatever exists: Terraform (`*.tf`), AWS CDK
   (`cdk.json`, `*-stack.ts/py`), CloudFormation/SAM (`template.yaml`,
   `serverless.yml`), Pulumi, or raw AWS CLI/boto usage. If none exist, review
   from the architecture the user describes. If read-only credentials exist you
   MAY run `describe-*`/`list-*` to confirm what's deployed.

2. **Assess each pillar,** but weight for stage. Check the load-bearing choices:
   - **Compute fit** — is it Lambda vs Fargate vs EC2/ASG vs EKS for the right
     reasons? Flag EKS or microservices adopted too early.
   - **Is a VPC/NAT actually needed,** or is it complexity/cost with no payoff?
   - **Managed vs self-hosted** — prefer managed/serverless unless there's a real
     reason not to (self-hosting a database or Kafka on a 3-person team is a red
     flag).
   - **Data layer** — RDS/Aurora Serverless v2/DynamoDB fit; Multi-AZ gives HA,
     not read scaling (that's read replicas).
   - Reliability, ops, and cost shape of each choice.

3. **Report.** Rank findings **P0/P1/P2**. For each: **Problem → Impact →
   Concrete fix** (the specific service swap or IaC change, ideally a diff). Note
   where the current setup is appropriately simple and should NOT be changed yet.
