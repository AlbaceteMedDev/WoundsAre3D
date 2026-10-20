---
name: aws-architecture-review
description: Review a startup's AWS architecture and pick services with a startup-pragmatic, Well-Architected lens. Use when the user asks to review their architecture, decide between AWS services (Lambda vs Fargate vs EC2, RDS vs DynamoDB), asks "should we use Kubernetes/EKS", "which AWS service for X", "do we need a VPC/NAT", or "is our setup well-architected".
---

# AWS Architecture Review (startup edition)

Grade the architecture against the six Well-Architected pillars, but weight them
for a small team. For a seed / Series-A company **Cost Optimization and
Operational Excellence dominate** — the biggest risk is not an outage, it's
burning runway or drowning a 3-person team in undifferentiated ops. Reliability
and Security get a pragmatic baseline; Performance and Sustainability are mostly
"don't do anything dumb" until a metric says otherwise.

This skill is part of `aws-startup-advisor`. It backs the
`/aws-startup-advisor:aws-architecture-review` command. For deep service-by-service
comparison tables, read `references/service-selection.md`.

## Step 1 — detect what they actually run

Read the repo before opining. Auto-detect IaC and infer the architecture:
- Terraform: `*.tf` (grep for `aws_ecs_`, `aws_lambda_`, `aws_db_instance`, `aws_instance`, `aws_eks_`, `aws_lb`, `aws_nat_gateway`).
- AWS CDK: `cdk.json`, `*-stack.ts` / `*-stack.py`.
- CloudFormation / SAM: `template.yaml`, `template.yml`.
- Serverless Framework: `serverless.yml`. Pulumi: `Pulumi.yaml`.
- Raw AWS CLI / boto3 usage in scripts.

If none exist, ask the user to describe the architecture (or read from the
account via read-only `aws ... describe/list` calls if creds are present) and
advise from that.

## The six pillars, startup-weighted

Walk each pillar and produce concrete findings, not a lecture.

- **Cost Optimization (heavy weight):** Is compute matched to load? Idle
  Multi-AZ RDS in dev? NAT Gateway where a gateway endpoint would do? On-demand
  everything with steady usage? Cross-AZ chatter? Cost is where startups bleed —
  hand deeper cost work to the `aws-cost-optimization` skill.
- **Operational Excellence (heavy weight):** Is infra in code (IaC) or clicked
  by hand? One-command deploy? Managed services over self-hosted so the team
  ships product, not babysits databases? Basic dashboards/alarms?
- **Reliability:** Multi-AZ for the primary datastore in prod. Health checks and
  autoscaling on the app tier. Backups that are actually tested. Stateless app
  servers. You do NOT need multi-region yet.
- **Security:** A baseline, not a program — private subnets for data, least-priv
  IAM roles (not access keys), no `0.0.0.0/0` to databases, secrets in Secrets
  Manager / SSM, encryption on. Defer to the `aws-security-baseline` skill.
- **Performance Efficiency:** Right instance/family (consider Graviton), a CDN
  for static assets, caching where a query is hot. Don't micro-optimize
  pre-traffic.
- **Sustainability:** Mostly falls out of right-sizing and serverless — turn off
  what you don't use. Not a standalone workstream at this size.

## Compute decision framework

Start at the top; take the first row that fits. Bias to managed.

1. **Event-driven, spiky, or low/unpredictable traffic, short tasks** → **Lambda**.
   Pay per request + GB-second, scales to zero. Watch cold starts and the
   per-invoke time/size ceilings.
2. **Long-running HTTP services or workers, containerized, want serverless** →
   **Fargate** (ECS). No servers to patch; billed per vCPU-second + GB-second.
   The default sweet spot for most startup backends.
3. **A single containerized web app / API without wanting to learn ECS wiring**
   → **App Runner**. Simplest path from container to URL; less control.
4. **Need GPUs, specific kernels, licensed AMIs, or steady 24/7 base load you'll
   commit** → **EC2 + Auto Scaling Group**. More ops; pair with a Compute
   Savings Plan / Graviton once usage is steady.
5. **EKS / Kubernetes** → only when you genuinely need its ecosystem AND have
   someone to own it. For ~3 services this is premature complexity; prefer ECS
   Fargate. See the "don't do this yet" list in the reference.

## Do you actually need a VPC and NAT Gateway?

- Pure Lambda + managed services (DynamoDB, S3, SQS) often need **no VPC** at all.
- If you do run in a VPC, put databases in **private subnets**. Private subnets
  reach AWS services either through a **NAT Gateway** (bills per-hour AND
  per-GB — a classic surprise) or, better, through **VPC endpoints**: gateway
  endpoints for **S3 and DynamoDB are free**; interface endpoints for other
  services cost hourly + per-GB but can still beat NAT.
- In non-prod, a single shared NAT (or a NAT instance for tiny workloads) is fine.
- Flag any architecture paying for NAT purely to reach S3/DynamoDB.

## Managed vs self-hosted

Default to managed. A small team should not run its own Postgres, Kafka, Redis,
Elasticsearch, or Kubernetes control plane unless a hard requirement forces it.
Use RDS/Aurora over self-managed Postgres, ElastiCache over self-run Redis, MSK
or SQS/SNS/EventBridge over self-hosted Kafka. The premium buys back engineer
time — the scarcest resource at a startup.

## Anti-patterns to flag

- EKS or a service mesh for a handful of services.
- Microservices before there's a team to own them — start modular monolith.
- Multi-region / active-active before there's a business reason.
- RDS Multi-AZ treated as read scaling (it is HA only — use **read replicas** to
  scale reads).
- A dedicated load balancer per tiny service instead of path/host routing on one.
- Hand-built infra with no IaC. NAT where a gateway endpoint fits.
- Self-hosting stateful infra a managed service already offers.

## Turn findings into a report

Produce a prioritized list. For each finding: **problem → impact (cost / risk /
ops burden) → concrete fix** (ideally the exact IaC diff or resource change).

- **P0** — actively costing money or a real reliability/security hole (idle
  Multi-AZ dev DB, NAT-only path to S3, DB open to `0.0.0.0/0`).
- **P1** — will bite within a quarter or as you grow (no autoscaling, stateful
  app servers, no IaC).
- **P2** — right-sizing and polish (Graviton migration, CDN for assets, tighter
  service boundaries).

End with a short "what NOT to do yet" note so the team doesn't over-build. For
the full service-selection tables and the premature-complexity catalog, read
`references/service-selection.md`.
