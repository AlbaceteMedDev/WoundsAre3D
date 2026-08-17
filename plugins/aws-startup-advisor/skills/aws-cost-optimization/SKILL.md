---
name: aws-cost-optimization
description: Control and cut AWS spend for a startup — right-size, eliminate waste, and prevent bill regressions. Use when the user says "our AWS bill is too high", "cut AWS costs", "why is AWS so expensive", "reduce spend", "right-size", "we got a surprise bill", or is chasing a cost anomaly.
---

# AWS Cost Optimization for Startups

Your job: make the monthly bill legible and smaller without kneecapping the team.
Optimize for cost AND engineering simplicity — a startup's most expensive resource
is usually engineering time, so prefer fixes that are cheap to keep true. Prefer
relative/structural savings over exact dollar promises; pricing moves, so if you
cite a figure, mark it "(verify current pricing)".

This skill pairs with the `/aws-startup-advisor:aws-cost-review` command, which
runs this method against the current repo and produces a ranked report.

## The cost-review method (run in order)

1. **Get visibility.** You cannot optimize what you cannot see. Confirm AWS
   Budgets + Cost Anomaly Detection are on, and that cost allocation tags are
   activated in the Billing console so spend breaks down by team/service/env.
   Without tags, every later step is guesswork.
2. **Find the top line items.** Cost is Pareto-distributed — a few services
   dominate. Point the user at Cost Explorer grouped by service, then by usage
   type. The usual suspects: compute (EC2/Fargate/Lambda), RDS, data transfer,
   NAT Gateway, S3, CloudWatch.
3. **Right-size.** Match provisioned capacity to real utilization before you
   commit to anything. Oversized instances, over-provisioned Lambda memory, and
   Multi-AZ in dev are pure waste — cutting them needs no commitment.
4. **Commit (only once usage is steady).** Cover the stable baseline with
   **Compute Savings Plans** (flexible across instance family, size, region, OS;
   also cover Fargate and Lambda). Don't lock in a 1- or 3-year commitment while
   architecture is still churning.
5. **Eliminate waste.** Idle databases, unattached EBS volumes, old snapshots,
   unused Elastic IPs, forgotten resources in other regions, dev environments
   left running nights/weekends.
6. **Prevent regressions.** Budgets with alerts, anomaly detection, a cost gate
   in review, and tagging enforced in IaC so the next expensive thing is caught
   before it ships.

## Detect the architecture first

Before advising, auto-detect and read the repo's IaC so findings are concrete:
Terraform (`*.tf`), AWS CDK (`cdk.json`, `*-stack.ts/py`), CloudFormation/SAM
(`template.yaml`, `serverless.yml`), Pulumi, or raw AWS CLI/boto usage. If the
repo has none, advise from the described architecture or read-only account data
instead. Always turn a finding into a concrete change: the file, the line, the diff.

## Checklist to run against the IaC

- **NAT Gateway** — bills per-hour AND per-GB processed; a top surprise cost.
  Look for `aws_nat_gateway` / NatGateway. Add **VPC gateway endpoints for S3 and
  DynamoDB (free)**; consider interface endpoints for chatty services; share one
  NAT in non-prod; a NAT instance can beat a NAT Gateway for tiny workloads.
- **Data transfer** — internet egress costs money and **cross-AZ traffic is
  charged in both directions**; same-AZ private-IP traffic is generally free.
  Flag chatty cross-AZ paths and traffic to S3/DynamoDB that should ride a
  gateway endpoint instead of the NAT.
- **RDS** — flag Multi-AZ on non-prod (roughly doubles instance cost for HA you
  don't need in dev), oversized instances, and idle databases. Remember **Multi-AZ
  is high availability, not read scaling** — use **read replicas** to scale reads,
  and consider **Aurora Serverless v2** for variable load.
- **Compute** — right-size before committing; move stable baseline to **Compute
  Savings Plans**; use **Graviton (ARM)** for ~20% better price/performance on
  compatible workloads; use **Spot** (up to ~90% off, ~2-min reclaim warning) for
  fault-tolerant/batch/stateless work only.
- **EBS** — migrate `gp2` → `gp3` (generally cheaper and more flexible); delete
  unattached volumes; enable account-level EBS default encryption per region.
- **Snapshots & EIPs** — prune old/orphaned snapshots; release unused Elastic IPs
  (an unattached EIP bills hourly).
- **S3** — it is billed for storage + requests + retrieval + egress (NOT free per
  request). Add lifecycle rules to IA/Glacier, abort incomplete multipart uploads,
  and use an **S3 gateway endpoint** so VPC traffic skips the NAT.
- **Lambda** — flag over-provisioned memory (you pay per GB-second); right-size
  from real duration/memory metrics.
- **CloudWatch Logs** — set retention; "never expire" log groups are a silent,
  compounding cost.
- **Load balancers** — an ALB per single service adds fixed hourly cost; consolidate
  or drop it where the service doesn't need it.
- **Dev environments** — schedule non-prod off nights/weekends; scan every region
  for forgotten resources.

For the full trap catalog — each with what it is, how to detect it, and the fix —
read `references/cost-traps.md`.

## Anti-patterns to flag

- Committing to Savings Plans / RIs before usage is steady, or before right-sizing.
- Chasing pennies (a $3/mo log group) while a $2k/mo idle Multi-AZ RDS sits untouched.
- Optimizing spend with no tags or budgets in place — you're flying blind.
- Trading large amounts of engineering time to save small, one-time dollars.
- Treating the **free tier** as permanent; it is a 12-month tier plus an always-free
  tier, and you should never architect assuming it lasts.

## Turn findings into a report

Rank by impact, not by ease. Group as **P0 / P1 / P2**:

- **P0** — big recurring waste or missing spend guardrails (idle Multi-AZ RDS,
  no budget/anomaly alert, NAT hauling S3 traffic).
- **P1** — meaningful right-sizing and commitment wins (Savings Plans on steady
  compute, gp2→gp3, Graviton, log retention).
- **P2** — cleanups and hygiene (orphaned snapshots/EIPs, dev scheduling, tag
  coverage gaps).

For each finding give: **problem → estimated impact (relative, and mark any dollar
figure "verify current pricing") → concrete fix (the file/line and a diff or exact
change) → rough effort**. Lead with the smallest number of changes that recover
the most spend.
