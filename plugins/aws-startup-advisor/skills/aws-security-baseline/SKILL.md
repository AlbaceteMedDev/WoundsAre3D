---
name: aws-security-baseline
description: Establish and audit a startup-achievable AWS security baseline — identity/IAM, account guardrails, data protection, network, and detection. Use when the user says things like "AWS security", "IAM", "are we secure on AWS", "least privilege", "secrets management", "harden our account", or "we need SOC2/HIPAA on AWS".
---

# AWS Security Baseline (startup edition)

The goal here is not "perfect security." It is the **minimum viable baseline a
3-person team can actually reach and keep**, ordered so the highest-leverage,
cheapest wins come first. Most AWS breaches trace back to identity mistakes and
publicly exposed data — not exotic attacks. Fix those first.

Compliance frameworks (SOC 2, HIPAA, PCI, ISO 27001) build **on top of** this
baseline; they do not replace it. If a startup can't pass this baseline, they
can't pass an audit. Get the baseline right, then layer compliance evidence.

## Priority order (do them in this order)

Work identity → guardrails → data → network → detection. Earlier layers stop
more damage per hour of effort.

1. **Identity** — who can touch the account, and how. The single biggest lever.
2. **Guardrails** — the account-wide audit log and spend/threat visibility.
3. **Data** — encryption at rest/in transit, no public buckets, backups.
4. **Network** — no accidental `0.0.0.0/0`, private subnets for data tiers.
5. **Detection** — GuardDuty/Security Hub so you *find out* when something drifts.

## The must-haves (P0 — do these regardless of stage)

- **Root user: MFA on, then stop using it.** Root is for a tiny set of tasks
  only. No root access keys — delete them if they exist. Day-to-day work happens
  through named identities.
- **Humans use IAM Identity Center (SSO), not IAM users.** Federate from Google
  Workspace / Okta / Entra. Every human gets MFA. This kills the "shared IAM
  user with long-lived keys in a Slack DM" pattern.
- **Workloads use IAM roles, never long-lived access keys.** ECS tasks, Lambda,
  EC2, and CI all assume roles. If you find `AKIA...` keys in code, env files, or
  Terraform, that's a P0 — rotate and move to roles / OIDC.
- **CloudTrail is on** (ideally a multi-Region org trail to a locked-down S3
  bucket). Without it you have no audit history when something goes wrong.
- **No public S3 buckets by accident.** Enable **S3 Block Public Access at the
  account level**. Buckets are encrypted by default (SSE-S3, since Jan 2023), but
  default encryption ≠ private — public access is a separate setting.
- **AWS Budgets + Cost Anomaly Detection.** A runaway bill is often the first
  visible symptom of compromised credentials (crypto mining). Cheap early alarm.

## Strong-next (P1)

- **Least-privilege IAM.** Kill `Action: "*"` / `Resource: "*"` policies. Scope
  to the services and ARNs actually used. Prefer AWS-managed job-function
  policies over hand-rolled wildcards early on.
- **Secrets in a secret store**, not env vars in the repo or plaintext Terraform.
  Use **AWS Secrets Manager** (rotation, cost per secret) or **SSM Parameter
  Store** (SecureString, cheaper) — pick one and be consistent.
- **Encryption everywhere it's free-ish.** Enable account-level **EBS default
  encryption** per Region; encrypt RDS; use **KMS** for anything sensitive.
- **GuardDuty on.** Managed threat detection, low effort, generous early cost.
  It catches compromised keys, crypto mining, and reconnaissance.
- **Security Hub** with the AWS Foundational Security Best Practices / CIS
  standard for an automated posture score you can chip away at.

## Nice-to-have / when the team grows (P2)

- **AWS Config** for resource-compliance rules and change history (useful audit
  evidence for SOC 2/HIPAA).
- **Multi-account via AWS Organizations** — separate prod/dev/security accounts.
  Real isolation, but only worth it once one account gets crowded.
- **VPC flow logs**, WAF in front of public endpoints, automated key rotation.
- **A HIPAA BAA with AWS** and a scoped, encrypted, access-logged data tier if
  handling PHI (private subnets, encrypted RDS, S3 object-lock, KMS) — confirm
  your own scope and regulated-data footprint.

## How to act in the current repo

Auto-detect the IaC first (Terraform `*.tf`; CDK `cdk.json`, `*-stack.ts/py`;
CloudFormation/SAM `template.yaml`, `serverless.yml`; Pulumi; or raw AWS CLI /
boto). Then grep for the tells:

- `0.0.0.0/0` on a security group ingress → check what port is exposed.
- `"Action": "*"` or `"Resource": "*"` in IAM policy JSON → over-broad grant.
- `AKIA` / `aws_access_key_id` / `aws_secret_access_key` in tracked files → keys
  in the repo.
- `acl = "public-read"` or missing Block Public Access on S3.
- `publicly_accessible = true` on RDS.
- Missing `storage_encrypted`, `kms_key_id`, or default-encryption settings.

If the repo has no IaC, reason from the account or the described architecture and
say what you'd verify in the console.

## Turn findings into a report

Rank gaps by severity, not by checklist order:

- **P0 (critical, fix now):** root without MFA / with keys, public buckets with
  data, long-lived keys in the repo, security group `0.0.0.0/0` on SSH/RDS/admin
  ports, CloudTrail off, wildcard admin policies attached to workloads.
- **P1 (soon):** broad IAM, secrets in env/plaintext, encryption not enforced,
  no GuardDuty, no budget alarm.
- **P2 (as you grow):** Config, multi-account, flow logs, automated rotation.

Each finding = **risk → concrete action → how to verify** (tool or console
check). Prefer a specific diff over generic advice.

For the full grouped, actionable checklist — with the risk, the fix, the grep,
and the AWS tool that satisfies each item — read
`references/security-checklist.md`.

This is the security specialist within `aws-startup-advisor`. It pairs with the
`/aws-startup-advisor:aws-security-baseline` command, which runs this framework
against the current repo and reports gaps by severity. For cost, architecture,
and scaling concerns, hand off to `aws-cost-optimization`,
`aws-architecture-review`, or `aws-scaling-plan`.
