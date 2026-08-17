# Service selection tables (startup edition)

Companion to the `aws-architecture-review` skill. Use these to justify a concrete
service pick with the trade-off spelled out. Default posture: **managed over
self-hosted, serverless over servers, boring over clever.** Cost figures are
structural, not quoted dollars — always confirm live numbers with the AWS
Pricing Calculator (verify current pricing).

## Compute

| Service | Pick when | Avoid when | Cost shape |
|---|---|---|---|
| **Lambda** | Event-driven, spiky, low or unpredictable traffic; short tasks; glue between services; cron. Scales to zero. | Long-running or steady high-throughput work where per-invoke ceilings, cold starts, or GB-second cost add up; heavy sustained CPU. | Per request + GB-second. Zero when idle; can get pricey at constant high volume. |
| **Fargate** (ECS) | Long-running containerized HTTP services and workers; you want serverless containers with no host patching. The default startup backend. | You need GPUs, custom kernels, or the very cheapest steady compute (commit EC2 instead). | Per vCPU-second + GB-second per task. Predictable; a bit above raw EC2 for equivalent steady load. |
| **App Runner** | One containerized web app / API and you want container-to-URL with minimal wiring; small teams avoiding ECS/ALB setup. | You need fine control over networking, sidecars, or complex multi-service topologies. | Per provisioned + active compute; simple but a premium for the convenience. |
| **EC2 + Auto Scaling Group** | Steady 24/7 base load you'll commit to; GPUs, licensed AMIs, or specific instance features; lift-and-shift. | You'd rather not patch, scale, and manage hosts; spiky or low traffic (serverless is cheaper and less work). | Per instance-hour. Cheapest per unit at steady load **with** a Compute Savings Plan + Graviton; you pay in ops time. |
| **EKS** (Kubernetes) | You truly need the k8s ecosystem (operators, portability, existing k8s expertise) AND have someone to own the cluster. | ~3 services, small team, no dedicated platform owner — this is premature complexity. Use ECS Fargate. | Control-plane hourly fee + all the node/networking cost + real operational overhead. |

**Cost levers that cut across compute:**
- **Graviton (ARM):** typically ~20% better price/performance for compatible
  workloads (most interpreted languages, many compiled ones). Cheap win on
  Fargate, Lambda, EC2, and RDS.
- **Compute Savings Plans:** 1- or 3-year commitment for a discount vs on-demand;
  flexible across instance family, size, region, OS, and also cover **Fargate and
  Lambda**. Don't commit until usage is steady.
- **Spot:** up to ~90% off on-demand, reclaimed with a ~2-minute warning. Great
  for fault-tolerant / batch / stateless workers; never for stateful singletons.

## Data stores

| Service | Pick when | Avoid when | Notes |
|---|---|---|---|
| **RDS** (Postgres/MySQL) | Default relational store; you want SQL, joins, transactions, and a managed engine. | You need infinite horizontal write scale or a truly serverless bill on bursty load. | **Multi-AZ = high availability, NOT read scaling** (standby serves no reads) and ~doubles instance cost — use it in prod, skip it in dev. Scale reads with **read replicas**. Idle non-prod instances are classic waste. |
| **Aurora Serverless v2** | Variable / bursty load where you want a Postgres/MySQL-compatible engine that scales capacity automatically. | Small, steady, cost-sensitive workloads where a right-sized RDS instance is simply cheaper. | Scales in fine-grained capacity units; can idle down. Verify it's cheaper than provisioned RDS for your pattern before switching. |
| **DynamoDB** | Known key-based access patterns, huge scale, or you want a serverless NoSQL bill that scales to near-zero; simple high-throughput lookups. | Ad-hoc queries, rich joins, analytics — access patterns that aren't designed up front. | On-demand or provisioned capacity. **Gateway endpoint is free** — never route DynamoDB through NAT. |
| **ElastiCache** (Redis/Memcached) | A hot query or session store is measurably hurting the DB; you need sub-ms cache or rate-limiting/locks. | You haven't proven a caching need yet — don't add a cache tier speculatively. | Managed; prefer over self-run Redis. Adds a stateful component, so add only when a metric demands it. |

## Async / messaging

| Service | Use for | Not for |
|---|---|---|
| **SQS** | Decoupling and load-shedding: buffer work, smooth spikes, retry with a dead-letter queue. One producer→consumer pipe. | Fan-out to many independent consumers (use SNS/EventBridge). |
| **SNS** | Simple pub/sub fan-out: one message to many subscribers (queues, Lambda, HTTP, email/SMS). | Rich content-based routing or event history/replay (use EventBridge). |
| **EventBridge** | Event bus with content-based routing rules, SaaS/AWS event sources, and scheduled events. The default "events" backbone. | A plain point-to-point work queue (SQS is simpler and cheaper). |
| **Step Functions** | Orchestrating a multi-step workflow with retries, branching, and state — where you'd otherwise hand-roll a state machine. | A single step or trivial chaining (just call it directly / from Lambda). |

Common pattern: **SQS in front of workers to shed load**, EventBridge to route
domain events, Step Functions only when a workflow has real branching/retry
state. Start with the least machinery that works.

## Networking quick reference

- No VPC needed for pure Lambda + DynamoDB/S3/SQS designs.
- In a VPC: databases in **private subnets**; egress via **NAT Gateway**
  (per-hour AND per-GB) or **VPC endpoints**.
- **S3 and DynamoDB gateway endpoints are free** — use them so VPC traffic skips
  the NAT. Interface endpoints cost hourly + per-GB but can beat NAT.
- **Cross-AZ traffic is billed both directions**; keep chatty components in one
  AZ where HA allows, and internet egress costs money.
- One shared load balancer with host/path routing beats a load balancer per tiny
  service.

## "Don't do this yet" — premature-complexity traps

For a seed / Series-A team, these usually cost more time and money than they
save. Flag them and recommend the simpler path until a real metric or requirement
forces the change.

- **EKS / Kubernetes for a handful of services.** Use **ECS Fargate**. Revisit
  only with a dedicated platform owner and a genuine k8s need.
- **Microservices before there's a team to own them.** Start with a modular
  monolith; split along a seam only when team or scale demands it.
- **Multi-region / active-active** before there's a business or compliance
  reason. It multiplies cost and operational complexity; Multi-AZ covers most
  reliability needs first.
- **Self-hosted Kafka / Elasticsearch / Redis / Postgres.** Use MSK or
  SQS/SNS/EventBridge, OpenSearch Service, ElastiCache, RDS/Aurora. A small team
  should not run stateful infra a managed service already offers.
- **A service mesh** (Istio/App Mesh) for a few services — pure overhead early.
- **RDS Multi-AZ as a read-scaling strategy.** It's HA only; use **read
  replicas** to scale reads, and skip Multi-AZ in dev entirely.
- **A CDN / cache tier / read replica added speculatively.** Add caching,
  CloudFront, ElastiCache, and replicas when latency or DB load metrics justify
  them — not before.
- **Over-engineered CI/CD or GitOps pipelines** before there's steady deploy
  volume. A simple, reliable one-command deploy beats an elaborate platform.
- **Custom autoscaling on hand-managed EC2** when a managed serverless option
  (Fargate/Lambda) would remove the problem outright.

When in doubt, recommend the simplest thing that works and note the metric that
would later justify graduating to the more complex option.
