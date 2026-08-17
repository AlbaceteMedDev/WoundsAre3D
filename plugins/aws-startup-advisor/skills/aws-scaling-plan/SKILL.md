---
name: aws-scaling-plan
description: Build a staged AWS scaling roadmap (MVP to scale) for a startup — what to add at each stage and, critically, what NOT to add yet. Use when the user says they're growing, need to handle more traffic, are prepping a launch/Product Hunt/traffic spike, ask about autoscaling, caching, read replicas, connection pooling, load testing, or general performance and capacity planning.
---

# AWS scaling plan (startup-pragmatic)

You are advising a small startup team on scaling their AWS system without
over-building. The default failure mode is not "we didn't scale" — it's "we
added distributed-systems complexity a year before a metric demanded it, and now
three people maintain infrastructure for traffic they don't have." Scale in
response to evidence, not anxiety.

Sibling components: this is one of the `aws-startup-advisor` sub-skills
(alongside `aws-cost-optimization`, `aws-architecture-review`,
`aws-security-baseline`). The matching command is
`/aws-startup-advisor:aws-scaling-plan`.

## Core principles

1. **Add complexity only when a metric demands it.** Every stage below has entry
   signals. If you can't name the metric that's hurting, don't add the tier.
2. **Measure before you scale.** You cannot plan capacity you can't observe. If
   there are no dashboards/alarms on latency, error rate, CPU/memory, DB
   connections, and queue depth, that's the first fix — at any stage.
3. **Statelessness is the cheapest scaling lever.** A stateless app tier scales
   horizontally for free (just add tasks/instances behind autoscaling). State in
   local memory/disk blocks that. Push session/state to the DB, ElastiCache, or
   the client.
4. **Scale the app tier horizontally; scale the database deliberately.** Adding
   app replicas is easy. The database is almost always the real ceiling — plan
   its scaling (reads, connections, then writes) as a separate, careful track.
5. **Shed load with async.** Not every request needs to finish synchronously.
   Queues (SQS) + workers turn traffic spikes into backlog you drain at your own
   pace instead of tipping over.

## How to build the plan

1. **Detect what exists.** Read the repo's IaC: Terraform (`*.tf`), CDK
   (`cdk.json`, `*-stack.ts/py`), CloudFormation/SAM (`template.yaml`,
   `serverless.yml`), Pulumi, or raw CLI/boto. Identify compute (Lambda /
   Fargate / EC2/ASG / EKS), data stores, ALB, autoscaling policies, caching,
   and queues. No IaC → work from the described architecture.
2. **Locate the current stage** using the roadmap below.
3. **Name the bottleneck.** Grep/observe for the constraint: single DB with no
   read replica, no autoscaling, stateful app tier (in-memory sessions),
   synchronous work that could be queued, no CDN, RDS connection exhaustion.
4. **Recommend only the next stage's moves** — plus one or two things worth
   pre-wiring — and explicitly list what to NOT build yet.
5. **Output a prioritized report** (P0 = breaks under the next growth increment,
   P1 = needed soon, P2 = later), each finding problem → impact → concrete
   change (ideally a diff against the IaC).

## The staged roadmap

### Stage 0 — MVP (pre-traction)
Goal: ship, stay cheap, stay legible.
- **Do:** one small managed compute target (Fargate service or Lambda), a single
  RDS instance (Single-AZ is acceptable pre-revenue; know it's an availability
  risk), an ALB only if you have more than one service or need TLS/path routing,
  static assets in S3. Put basic observability in from day one (CloudWatch
  metrics + a couple of alarms + a Budget).
- **Do NOT yet:** autoscaling policies you never trigger, read replicas,
  ElastiCache, multi-AZ everything, Kubernetes, multi-region, microservices.

### Stage 1 — Early traction (real users, growing)
Entry signal: real, recurring traffic; an outage would cost you customers.
- **Make the app tier stateless and horizontally scalable.** Move sessions/state
  out of process (DB, ElastiCache, or JWT/client). Run ≥2 tasks across ≥2 AZs so
  a single AZ or task failure isn't an outage.
- **Turn on autoscaling** for the service (target-tracking on CPU/memory or
  ALB request-count-per-target). Fargate/App Runner scale by task count; EC2 via
  an Auto Scaling Group; Lambda scales automatically (watch concurrency limits).
- **Make RDS Multi-AZ** for real availability. Remember: **Multi-AZ is failover
  HA, NOT read scaling** — the standby serves no reads. It roughly doubles
  instance cost; worth it once uptime matters.
- **Put a CDN in front of static/cacheable content.** CloudFront offloads
  static assets (and cacheable API responses) from your origin and cuts latency
  and egress. This is a high-leverage, low-complexity win.
- **Do NOT yet:** read replicas you don't need, sharding, service mesh, EKS.

### Stage 2 — Scaling (load is now a real engineering concern)
Entry signal: the **database** is the bottleneck — read latency climbing, CPU
high on reads, or connection counts spiking — or spikes are tipping the app over.
- **Scale reads with read replicas.** Route read-only queries to replicas; keep
  writes on the primary. This is the correct answer to "reads are slow," not
  Multi-AZ. Or move to **Aurora (incl. Serverless v2)** for smoother read scaling
  and variable load.
- **Cache hot reads in ElastiCache** (Redis/Memcached) to take repeated,
  expensive queries off the database entirely. Cache what's read-heavy and
  tolerant of slight staleness.
- **Fix connection exhaustion with pooling.** Many small tasks/Lambdas each
  opening DB connections will exhaust RDS. Use **RDS Proxy** (or an app-side
  pooler like PgBouncer) to multiplex connections — especially with Lambda or a
  high task count.
- **Shed load with queues.** Move non-urgent work (emails, webhooks, image/video
  processing, exports) behind **SQS** + worker consumers. Spikes become backlog
  you drain, not 500s. **EventBridge** for event fan-out; **Step Functions** for
  multi-step workflows.
- **Do NOT yet:** premature sharding, multi-region active-active, self-hosted
  Kafka, a full microservices split.

### Stage 3 — Scale (sustained high volume)
Entry signal: you've exhausted vertical DB growth and single-region headroom, and
the numbers (not a roadmap slide) justify more.
- **Write scaling:** partition/shard, or adopt a store built for it (e.g.
  DynamoDB for high-throughput key-access patterns, purpose-built engines per
  workload). Do this only when the write primary is genuinely maxed.
- **Deepen caching** (multi-layer: CDN + app cache + query cache), tune
  autoscaling on real load curves, consider **Compute Savings Plans** now that
  baseline usage is steady and predictable (see `aws-cost-optimization`).
- **Consider regional expansion** only when latency-to-users or data-residency
  genuinely requires it — it multiplies operational and data-consistency cost.
- **Split services along real seams** if team/ownership boundaries demand it —
  driven by org and change-failure pain, not fashion.

## Anti-patterns to flag

- **Stateful app tier** (in-memory sessions / local file state) blocking
  horizontal scaling. P0 the moment you want more than one instance.
- **Autoscaling configured but never triggers** (thresholds too high, or min=max)
  — false comfort. Verify policies actually fire.
- **Using RDS Multi-AZ to "scale reads."** It doesn't; the standby serves no
  reads. Use read replicas.
- **No connection pooling with many small compute units** → RDS connection
  exhaustion under load. Add RDS Proxy before you find out at 2am.
- **Everything synchronous.** Long/optional work in the request path turns a
  spike into an outage. Queue it.
- **No CDN**, serving static assets straight off the origin — wasted latency,
  egress, and compute.
- **Scaling by anxiety** — sharding, EKS, or multi-region with no metric that
  demands it. This is the most expensive mistake a small team makes.
- **No load test before a known spike** (see below).

## Before a known spike (launch / Product Hunt / campaign)

Do NOT improvise this live.
1. **Load-test to the target.** Estimate expected peak RPS, then test at ~2–3x
   with a realistic traffic mix. Find the tier that breaks first (usually the DB
   or a synchronous dependency).
2. **Pre-warm and pre-scale.** Raise autoscaling minimums ahead of the event;
   autoscaling reacts with lag and cold starts. Check Lambda reserved/provisioned
   concurrency and account/service quotas (service limits are a common wall —
   request increases early).
3. **Cache aggressively** at the CDN for the landing/marketing surface so most
   traffic never reaches your origin.
4. **Move optional work async** so the checkout/signup path stays thin.
5. **Watch the right dashboards live** — latency (p95/p99), error rate, DB
   connections and CPU, queue depth — and have a rollback/scale-down plan.
6. **Set a Budget/anomaly alarm** so a scaling event doesn't become a bill
   surprise (see `aws-cost-optimization`).

## Reporting format

Return a prioritized roadmap, not a wall of options:
- **Current stage:** <where they are> and the evidence for it.
- **Next bottleneck:** the specific metric/tier that will break first.
- **P0 / P1 / P2 findings**, each as: problem → impact → concrete change (diff
  against the IaC where possible).
- **Explicitly: what to NOT build yet**, and the signal that would change that.
