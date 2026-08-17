# AWS Cost Traps — Detailed Catalog

The concrete, recurring ways startups overpay on AWS. This is the depth companion
to `../SKILL.md`; use it to identify a specific trap and act on it. Each trap uses
the same structure:

- **What it is** — the mechanism that costs money.
- **Detect** — what to grep/look for in IaC or the bill.
- **Fix** — the concrete change.

Rank findings by recurring impact, not by how easy they are to fix. Prefer
relative/structural savings; if you cite a dollar figure, mark it
"(verify current pricing)". Never claim NAT/data transfer is free, that S3 has no
per-request cost, that RDS Multi-AZ scales reads, or that the free tier is permanent.

---

## 1. NAT Gateway (and missing VPC endpoints)

- **What it is** — a NAT Gateway bills **per-hour for the gateway AND per-GB
  processed**. It is one of the most common surprise line items. Traffic from
  private subnets to S3, DynamoDB, ECR, and other AWS services routes through the
  NAT by default and racks up per-GB processing charges for data that never needs
  to leave AWS's network.
- **Detect** — grep IaC for `aws_nat_gateway`, `NatGateway`, `natGateways`. Count
  how many (one per AZ is common and multiplies the hourly charge). In the bill,
  look at the `NatGateway-Hours` and `NatGateway-Bytes` usage types. High
  NatGateway-Bytes with S3/DynamoDB in the architecture is the tell.
- **Fix** — add **VPC gateway endpoints for S3 and DynamoDB (free)** so that
  traffic skips the NAT entirely. For other chatty services (ECR, Secrets Manager,
  CloudWatch Logs, SSM), add **interface endpoints** — they bill hourly + per-GB
  but can beat NAT for high volume. In non-prod, share a **single NAT** across AZs
  instead of one per AZ. For tiny workloads, a **NAT instance** on a small Graviton
  box can be cheaper than a managed NAT Gateway. Only run private subnets + NAT if
  you actually need private egress (see the architecture skill).

## 2. Cross-AZ and internet-egress data transfer

- **What it is** — internet egress costs money, and **cross-AZ traffic is charged
  in both directions**. Same-AZ traffic over private IPs is generally free. Chatty
  services spread across AZs (app ↔ database, service ↔ cache, inter-service calls)
  quietly accumulate cross-AZ charges. Egress to the internet (including to other
  clouds or users) is billed per-GB and rises with scale.
- **Detect** — in the bill, look for `DataTransfer-Regional-Bytes` (cross-AZ) and
  `DataTransfer-Out-Bytes` (internet egress). In IaC, look for resources pinned to
  different AZs that talk constantly, and for traffic to S3/DynamoDB routed through
  the NAT rather than a gateway endpoint.
- **Fix** — keep tightly-coupled chatty components in the same AZ where availability
  allows; use gateway endpoints for S3/DynamoDB; put a CDN (CloudFront) in front of
  high-egress content so bytes are served from cache; compress payloads. Don't
  prematurely spread everything across three AZs "for reliability" if the cross-AZ
  chatter outweighs the benefit for your stage.

## 3. Idle / oversized RDS and Multi-AZ in dev

- **What it is** — databases are often the single largest line item. **Multi-AZ
  gives high availability, NOT read scaling** (the standby does not serve reads)
  and roughly **doubles instance cost**. Running Multi-AZ in dev/staging pays for
  HA you don't need. Oversized instances and idle non-prod databases left running
  24/7 are classic waste.
- **Detect** — grep IaC for `multi_az = true` / `MultiAZ: true` and check whether
  it is on a non-prod instance. Check `instance_class` against real CPU/memory/
  connection metrics. Look for databases with near-zero connections in CloudWatch.
- **Fix** — turn off Multi-AZ in non-prod. Right-size instance classes to observed
  utilization. Stop or downsize idle non-prod databases (schedule them off nights/
  weekends). To scale reads, add **read replicas** — do not reach for Multi-AZ. For
  spiky or variable load, evaluate **Aurora Serverless v2**, which scales capacity
  with demand.

## 4. Oversized / on-demand compute (Savings Plans, Graviton, Spot)

- **What it is** — paying full on-demand rates for a steady baseline, running
  oversized instances, and using x86 where ARM would do. A stable workload on
  pure on-demand leaves a large, predictable discount on the table.
- **Detect** — in the bill, look for consistent 24/7 on-demand EC2/Fargate/Lambda
  usage with no Savings Plan coverage (Cost Explorer's coverage/utilization
  reports). In IaC, check instance sizes vs. utilization metrics, and whether
  workloads run on Graviton (`arm64`) or x86 (`x86_64`).
- **Fix** — right-size **first**, then cover the steady baseline with **Compute
  Savings Plans** (flexible across instance family, size, region, OS; also cover
  Fargate and Lambda) — but only once usage is steady and architecture has settled.
  Move compatible workloads to **Graviton (ARM)** for typically ~20% better
  price/performance. Run fault-tolerant/batch/stateless jobs on **Spot** (up to
  ~90% off on-demand, reclaimed with a ~2-minute warning) — never stateful
  singletons. RIs are an option but are more specific than Savings Plans; prefer
  Savings Plans for flexibility.

## 5. EBS gp2 → gp3 and unattached volumes

- **What it is** — `gp2` volumes are generally more expensive and less flexible
  than **`gp3`**, which decouples IOPS/throughput from size. Volumes left behind
  after instances terminate keep billing while attached to nothing.
- **Detect** — grep IaC for `type = "gp2"` / `VolumeType: gp2`. For orphans, look
  for volumes in `available` (not `in-use`) state via a read-only
  `aws ec2 describe-volumes` filter, or unreferenced volume resources in IaC.
- **Fix** — migrate `gp2` → `gp3` (can be done in place; then tune IOPS/throughput
  to actual need). Delete unattached volumes after confirming they're not needed.
  Enable account-level **EBS default encryption** per region while you're in there.

## 6. Old snapshots and unused Elastic IPs

- **What it is** — EBS/RDS snapshots accumulate forever unless pruned, each billing
  for storage. An **Elastic IP that is not attached to a running resource bills
  hourly** (allocated-but-idle EIPs are charged).
- **Detect** — read-only `aws ec2 describe-snapshots --owner-ids self` and RDS
  snapshot lists; look for large numbers of old, manual snapshots with no lifecycle
  policy. `aws ec2 describe-addresses` for EIPs with no association. In IaC, look
  for `aws_eip` resources not wired to an instance/NAT.
- **Fix** — adopt a snapshot lifecycle/retention policy (e.g. Data Lifecycle
  Manager) and delete stale manual snapshots. Release EIPs you aren't using.

## 7. S3 storage class, lifecycle, and incomplete multipart uploads

- **What it is** — S3 is billed for **storage + requests + retrieval + egress — it
  is NOT free per request**. Everything sitting in Standard forever, no lifecycle
  transitions, and **incomplete multipart uploads** (partial uploads that were never
  completed or aborted) all silently accrue storage cost. Buckets are **encrypted by
  default (SSE-S3) since January 2023**, so encryption is not the cost lever here —
  storage class and lifecycle are.
- **Detect** — check for `aws_s3_bucket_lifecycle_configuration` / `LifecycleRules`
  in IaC; their absence on large buckets is the trap. In the bill, look at S3 usage
  types by storage class and at request counts. Use S3 Storage Lens / a bucket
  metrics report to spot incomplete multipart uploads.
- **Fix** — add **lifecycle rules** to transition cold data to IA/Glacier and expire
  what you don't need; add a rule to **abort incomplete multipart uploads** after
  N days; put an **S3 gateway endpoint** on the VPC so bucket traffic skips the NAT
  (see trap #1). Right-size storage class to access patterns rather than leaving
  everything in Standard.

## 8. Over-provisioned Lambda memory

- **What it is** — Lambda bills **per request + per GB-second**, so memory is a
  direct cost multiplier. Functions provisioned at 1024 MB "to be safe" when they
  use 150 MB pay several times over. (Note: more memory also means more CPU, so the
  cheapest setting isn't always the smallest — tune, don't just minimize.)
- **Detect** — grep IaC for `memory_size` / `MemorySize` and compare against the
  `Max Memory Used` reported in CloudWatch Logs / Lambda metrics. Large gaps are
  the signal.
- **Fix** — right-size memory from observed max usage (Lambda Power Tuning helps
  find the cost/latency sweet spot). Lambda is excellent for spiky/low/unpredictable
  traffic; for steady high-throughput workloads, compare against Fargate.

## 9. CloudWatch Logs retention (and log volume)

- **What it is** — log groups default to **never expire**, so ingested logs are
  stored and billed indefinitely. High-cardinality debug logging compounds both
  ingestion and storage cost.
- **Detect** — grep IaC for `aws_cloudwatch_log_group` without a `retention_in_days`,
  or log groups showing "Never expire" in the console. Check the CloudWatch line in
  the bill for storage vs. ingestion.
- **Fix** — set an explicit **retention** on every log group (e.g. 30–90 days for
  app logs), export anything you must keep long-term to S3 with a lifecycle policy,
  and trim noisy debug logging in hot paths.

## 10. Load balancers for a single service

- **What it is** — every ALB/NLB carries a fixed hourly charge plus capacity-unit
  charges. One load balancer per small single-container service adds up fast when
  the service doesn't need it.
- **Detect** — grep IaC for `aws_lb` / `LoadBalancer` and count them against the
  number of services actually needing external ingress. Multiple ALBs fronting one
  service each is the smell.
- **Fix** — consolidate services behind a shared ALB using host/path routing; for a
  single containerized web service, consider **App Runner** or Fargate with a single
  shared ingress. Drop the load balancer where the service is internal or serverless
  and doesn't require it.

## 11. Dev environments left running nights and weekends

- **What it is** — non-prod EC2/RDS/ECS running 24/7 pays for ~168 hours/week when
  the team uses it for ~40. That's roughly a 75% waste on non-prod compute for
  environments no one touches off-hours.
- **Detect** — identify non-prod resources (by tag/name/env) that run continuously.
  Absence of any stop/start schedule or autoscaling-to-zero is the trap.
- **Fix** — schedule non-prod to stop nights/weekends (Instance Scheduler, an
  EventBridge + Lambda stop/start, or scaling ASGs/services to zero). Tag by
  environment so the schedule can target non-prod precisely.

## 12. Forgotten resources in unused regions

- **What it is** — a resource spun up in another region for a test, a leftover NAT
  Gateway, an orphaned load balancer, or an idle instance keeps billing in a region
  no one looks at. Cost Explorer defaults hide it because attention lives in the
  primary region.
- **Detect** — read-only sweep across regions (e.g. iterate `aws ec2
  describe-instances` / `describe-nat-gateways` / `elbv2 describe-load-balancers`
  per region, or use Cost Explorer grouped by region) for anything running outside
  the intended region(s).
- **Fix** — delete confirmed-orphaned resources; restrict new deployments to
  approved regions (Service Control Policies / IAM region conditions); add a
  periodic multi-region sweep to catch strays.

---

## Turning the catalog into a report

Map each confirmed trap into the **P0 / P1 / P2** structure from the skill:

- **P0** — large recurring waste or a missing spend guardrail (idle Multi-AZ RDS,
  NAT hauling S3/DynamoDB traffic with no gateway endpoint, no budget/anomaly alert).
- **P1** — meaningful right-sizing and commitment wins (Savings Plans on steady
  compute, Graviton migration, gp2→gp3, log retention, Lambda memory).
- **P2** — hygiene and cleanups (orphaned snapshots/EIPs, dev scheduling, unused
  region strays, lifecycle rules on cold buckets).

For each: **problem → relative impact (mark any dollar figure "verify current
pricing") → concrete fix (file/line + diff or exact change) → rough effort**. Lead
with the fewest changes that recover the most recurring spend.
