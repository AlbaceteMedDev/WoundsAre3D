# AWS Security Baseline — Actionable Checklist

Grouped, prioritized security checks for a startup on AWS. Each item states the
**risk**, the **action** (the fix), a **check** (how Claude verifies it in IaC or
the console), and the **tool** that satisfies it. Work top to bottom within each
group; groups are ordered by leverage (identity first, detection last).

Severity legend: **P0** fix now · **P1** soon · **P2** as the team grows.

---

## 1. Account & Identity

### 1.1 Root user has MFA and no access keys — **P0**
- **Risk:** Root can do anything, including closing the account and removing
  guardrails. A compromised root is game over.
- **Action:** Enable hardware or virtual MFA on root. Delete all root access
  keys. Use root only for the handful of tasks that require it.
- **Check:** IAM console credential report / `aws iam get-account-summary`
  (`AccountMFAEnabled` = 1, `AccountAccessKeysPresent` = 0). Root keys never
  appear in IaC — check the account.
- **Tool:** IAM, Security Hub CIS check flags this automatically.

### 1.2 Humans authenticate via IAM Identity Center (SSO) — **P1**
- **Risk:** Standalone IAM users mean shared credentials, orphaned accounts when
  people leave, and long-lived keys.
- **Action:** Enable **IAM Identity Center**, federate to your IdP (Google/Okta/
  Entra), enforce MFA, assign permission sets. Retire human IAM users.
- **Check:** Look for `aws_iam_user` resources in Terraform — each human user is
  a smell. SSO is usually configured in the console, not IaC.
- **Tool:** IAM Identity Center.

### 1.3 Workloads use IAM roles, not long-lived keys — **P0**
- **Risk:** Static `AKIA...` keys leak (repos, laptops, CI logs) and rarely get
  rotated. The most common root cause of AWS account compromise.
- **Action:** Give ECS tasks/Lambda/EC2 instance roles; give CI OIDC-federated
  roles (GitHub Actions OIDC → IAM role). Delete standing access keys.
- **Check:** `grep -rEn 'AKIA[0-9A-Z]{16}|aws_secret_access_key|aws_access_key_id'`
  across the repo; look for `aws_iam_access_key` resources in Terraform.
- **Tool:** IAM roles, GitHub OIDC provider, GuardDuty (flags key misuse).

### 1.4 Least-privilege IAM — no wildcard admin on workloads — **P1**
- **Risk:** An over-permissioned role turns a small app compromise into a full
  account compromise.
- **Action:** Scope policies to the specific actions and resource ARNs used.
  Start from AWS-managed job-function policies; avoid hand-rolled `*`.
- **Check:** `grep -rEn '"(Action|Resource)"\s*:\s*"\*"'` in policy JSON/HCL.
  Flag `AdministratorAccess` attached to app or CI roles.
- **Tool:** IAM Access Analyzer (unused-access + policy generation), Security Hub.

### 1.5 Access keys and credentials are rotated — **P2**
- **Risk:** The longer a credential lives, the more places it has leaked to.
- **Action:** Eliminate long-lived keys first (see 1.3); rotate anything that
  must remain. Alert on keys older than ~90 days.
- **Check:** IAM credential report `access_key_last_rotated`.
- **Tool:** IAM Access Analyzer, Config rule `access-keys-rotated`.

---

## 2. Logging & Detection

### 2.1 CloudTrail is enabled (multi-Region org trail) — **P0**
- **Risk:** No audit trail = no way to investigate an incident or prove what
  happened for a compliance audit.
- **Action:** Enable a **multi-Region CloudTrail** delivering to a dedicated,
  access-restricted S3 bucket (ideally with object-lock and in a separate
  account). Enable log-file validation.
- **Check:** Terraform `aws_cloudtrail` with `is_multi_region_trail = true` and
  `enable_log_file_validation = true`; confirm the bucket blocks public access.
- **Tool:** CloudTrail.

### 2.2 GuardDuty is on — **P1**
- **Risk:** Compromised keys, crypto-mining, and reconnaissance go unnoticed.
- **Action:** Enable **GuardDuty** in every active Region (delegate admin from
  the org if multi-account). Route findings to a real inbox/Slack.
- **Check:** `aws_guardduty_detector` in IaC, or GuardDuty console status.
- **Tool:** GuardDuty.

### 2.3 Security Hub posture scoring — **P1**
- **Risk:** Config drift accumulates silently; nobody has a scoreboard.
- **Action:** Enable **Security Hub** with AWS Foundational Security Best
  Practices and/or CIS AWS Foundations; work the failing controls down over time.
- **Check:** `aws_securityhub_account` / `aws_securityhub_standards_subscription`
  in IaC, or the Security Hub dashboard.
- **Tool:** Security Hub.

### 2.4 AWS Config change tracking — **P2**
- **Risk:** No history of who changed which resource when; weak audit evidence.
- **Action:** Enable **AWS Config** recorder + the managed conformance rules that
  matter (encryption, public access, key rotation).
- **Check:** `aws_config_configuration_recorder` / `aws_config_config_rule`.
- **Tool:** AWS Config.

### 2.5 Budget + Cost Anomaly Detection alarms — **P0**
- **Risk:** A stolen key spun up on crypto mining shows up as a bill spike; an
  unmonitored account can rack up thousands before anyone notices.
- **Action:** Set an **AWS Budget** with alert thresholds and **Cost Anomaly
  Detection**. Treat a sudden spike as a possible security event.
- **Check:** `aws_budgets_budget` in IaC; confirm a subscriber email exists.
- **Tool:** AWS Budgets, Cost Anomaly Detection.

---

## 3. Data Protection

### 3.1 S3 Block Public Access at the account level — **P0**
- **Risk:** Public buckets are a top cause of real data leaks. Default
  encryption (SSE-S3, on by default since Jan 2023) does **not** make a bucket
  private — public access is a separate control.
- **Action:** Turn on **account-level Block Public Access**; keep it on per
  bucket. Only expose objects through CloudFront/OAC, never a public bucket.
- **Check:** `grep -rEn 'acl\s*=\s*"public-read"|"AllUsers"|ignore_public_acls\s*=\s*false'`;
  look for missing `aws_s3_bucket_public_access_block`.
- **Tool:** S3 Block Public Access, IAM Access Analyzer (external-access finding).

### 3.2 Encryption at rest is enforced — **P1**
- **Risk:** Unencrypted volumes/databases/buckets fail audits and expose data if
  a snapshot or disk leaks.
- **Action:** Enable **account-level EBS default encryption** per Region; set
  `storage_encrypted = true` on RDS; use **KMS** CMKs for sensitive data.
- **Check:** RDS missing `storage_encrypted`; EBS `encrypted` unset; S3 buckets
  without a bucket-key/KMS setting where CMK is required.
- **Tool:** KMS, EBS default encryption, RDS encryption.

### 3.3 Encryption in transit — **P1**
- **Risk:** Plaintext traffic can be intercepted.
- **Action:** Terminate TLS at the ALB/CloudFront; use ACM certs; enforce
  HTTPS-only (redirect HTTP); require SSL on RDS/Redis where supported.
- **Check:** ALB listener on port 80 without a redirect to 443; `aws_acm_*`
  present; RDS parameter groups enforcing SSL.
- **Tool:** ACM, ELB/CloudFront TLS policies.

### 3.4 Backups and immutability — **P1**
- **Risk:** Ransomware or fat-finger deletion with no recovery path.
- **Action:** Enable automated RDS backups + PITR; version critical S3 buckets;
  use **object-lock** for records that must be tamper-proof; test restores.
- **Check:** RDS `backup_retention_period > 0`; S3 `versioning`/`object_lock`
  config on critical buckets.
- **Tool:** AWS Backup, S3 Versioning + Object Lock.

---

## 4. Network

### 4.1 No `0.0.0.0/0` ingress on sensitive ports — **P0**
- **Risk:** SSH (22), RDP (3389), database (5432/3306), and admin ports open to
  the whole internet are scanned and attacked within minutes.
- **Action:** Restrict ingress to known CIDRs or a bastion/SSM Session Manager.
  Prefer **SSM Session Manager** over open SSH entirely.
- **Check:** `grep -rEn 'cidr_blocks\s*=\s*\["0\.0\.0\.0/0"\]'` and match against
  the port; `from_port`/`to_port` covering 22/3389/5432/3306.
- **Tool:** Security Groups, SSM Session Manager, Security Hub checks.

### 4.2 Data tier lives in private subnets — **P1**
- **Risk:** Databases/caches reachable from the internet dramatically widen the
  attack surface.
- **Action:** Put RDS/ElastiCache in **private subnets**; only the ALB (and
  bastion/SSM) are public. Set RDS `publicly_accessible = false`.
- **Check:** `grep -rEn 'publicly_accessible\s*=\s*true'`; subnet associations
  for data resources.
- **Tool:** VPC private subnets.

### 4.3 VPC flow logs — **P2**
- **Risk:** No network-level forensic record during an incident.
- **Action:** Enable **VPC flow logs** to CloudWatch/S3 (set a sane retention).
- **Check:** `aws_flow_log` resources in IaC.
- **Tool:** VPC Flow Logs.

### 4.4 Edge protection for public endpoints — **P2**
- **Risk:** Public apps face L7 attacks, bots, and volumetric abuse.
- **Action:** Front public endpoints with **CloudFront + AWS WAF** managed rule
  groups once you have real public traffic.
- **Check:** `aws_wafv2_*` / CloudFront distributions on public ALBs.
- **Tool:** AWS WAF, CloudFront, Shield Standard (automatic).

---

## 5. Secrets

### 5.1 Secrets live in a secret store, not the repo — **P0**
- **Risk:** API keys, DB passwords, and tokens committed to Git or baked into
  images leak permanently (Git history keeps them).
- **Action:** Store secrets in **AWS Secrets Manager** (rotation, per-secret
  cost) or **SSM Parameter Store SecureString** (cheaper). Inject at runtime.
- **Check:** `grep -rEn 'password\s*=|secret\s*=|token\s*=|api[_-]?key'` in
  tracked files; plaintext values in `.tfvars`/`variables.tf`; secrets echoed in
  CI logs.
- **Tool:** Secrets Manager, SSM Parameter Store, KMS (encrypts both).

### 5.2 No secrets in environment/state in plaintext — **P1**
- **Risk:** Terraform state and CI env dumps expose secrets to anyone with read
  access.
- **Action:** Keep Terraform state in an encrypted, locked, access-restricted S3
  backend; mark variables `sensitive`; pull secrets at deploy time, not commit.
- **Check:** Backend config for encryption; `sensitive = true` on secret vars;
  secrets hardcoded in `env` blocks of task/Lambda definitions.
- **Tool:** S3 encrypted backend, Secrets Manager references in task defs.

### 5.3 Rotation for the secrets that matter — **P2**
- **Risk:** A leaked-but-unrotated secret stays valid indefinitely.
- **Action:** Enable Secrets Manager rotation for DB creds and high-value keys.
- **Check:** `rotation_rules` on `aws_secretsmanager_secret_rotation`.
- **Tool:** Secrets Manager rotation.

---

## 6. CI/CD & Keys

### 6.1 CI authenticates via OIDC, not stored keys — **P0**
- **Risk:** Long-lived deploy keys stored in CI secrets are a prime theft target
  with broad permissions.
- **Action:** Use **GitHub Actions OIDC** (or your CI's equivalent) to assume a
  scoped IAM role. No standing `AKIA` keys in CI.
- **Check:** Look for `aws-access-key-id` in workflow YAML vs. an OIDC
  `role-to-assume`; an `aws_iam_openid_connect_provider` for the CI host.
- **Tool:** IAM OIDC provider, scoped deploy role.

### 6.2 Deploy roles are least-privilege — **P1**
- **Risk:** A CI compromise with an admin deploy role = full account compromise.
- **Action:** Scope the deploy role to exactly what the pipeline changes; split
  plan (read) vs apply (write) where practical.
- **Check:** Policy attached to the CI role; flag `AdministratorAccess`.
- **Tool:** IAM, IAM Access Analyzer.

### 6.3 Secret scanning on the repo — **P1**
- **Risk:** Secrets get committed despite best intentions.
- **Action:** Enable push-protection secret scanning; add a pre-commit hook
  (e.g. gitleaks/trufflehog). Treat any hit as rotate-immediately.
- **Check:** Presence of a scanning config / pre-commit hook; run a scan.
- **Tool:** Repo secret scanning + push protection.

---

## Compliance note

SOC 2, HIPAA, PCI, and ISO 27001 all **assume** this baseline is in place, then
add evidence, formal policies, and access reviews on top. Notably: sign a **HIPAA
BAA with AWS** before putting PHI on it, keep PHI encrypted with KMS in a private,
access-logged tier, and retain CloudTrail/Config as audit evidence. If any
control here is failing, fix it before pursuing certification — auditors check
these first.

For the priority framework and how to route to sibling components, see the
parent `SKILL.md`.
