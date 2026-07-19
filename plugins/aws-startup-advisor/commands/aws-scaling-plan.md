---
description: Produce a staged AWS scaling roadmap for the current system, optionally targeting a growth scenario.
argument-hint: "[optional-scenario: e.g. 10x traffic, Product Hunt launch]"
allowed-tools: Read, Grep, Glob, Bash, WebFetch
---

Produce a staged scaling roadmap for the current system. Apply the
`aws-scaling-plan` skill (its MVP → early traction → scaling → scale stages).
The point is a plan that adds complexity **only when a metric demands it** — call
out explicitly what NOT to build yet.

Scenario: if `$ARGUMENTS` names a target (e.g. "10x traffic", "Product Hunt
launch", "handle 5k concurrent users"), plan for that specific spike. Otherwise
give a general roadmap for the system as it stands.

1. **Detect the IaC and understand today's shape.** Read whatever exists:
   Terraform (`*.tf`), AWS CDK (`cdk.json`, `*-stack.ts/py`), CloudFormation/SAM
   (`template.yaml`, `serverless.yml`), Pulumi, or raw AWS CLI/boto usage. If
   none exist, work from the described architecture. Identify the likely first
   bottleneck (usually the database, then stateful app nodes).

2. **Map the current setup onto the stages** and find what's missing for the next
   one. Consider, roughly in order of when they matter:
   - **Statelessness** first — nothing scales horizontally until app nodes are
     stateless (sessions/uploads off local disk).
   - **Autoscaling** (ASG / Fargate / Lambda concurrency) driven by a real metric.
   - **Caching** — CloudFront/CDN for static and cacheable responses; ElastiCache
     for hot data — before scaling the database.
   - **Read replicas** to scale reads (Multi-AZ is HA, not read scaling).
   - **Queues/async** (SQS/EventBridge) to shed spiky load off the request path.
   - **Connection pooling** (RDS Proxy) once Lambda/many nodes exhaust DB
     connections.
   - **Load testing** before any known spike.

3. **Report a staged roadmap.** For each stage: the trigger metric that means
   "do this now", what to add, and — critically — what to defer. Rank the
   immediate actions **P0/P1/P2**, each as **Problem/limit → Impact at target
   load → Concrete change** (the specific service or IaC edit). If a scenario was
   given, end with a pre-spike checklist (load test, autoscaling headroom, DB
   connection ceiling, cache warmup, budget/anomaly alarms).
