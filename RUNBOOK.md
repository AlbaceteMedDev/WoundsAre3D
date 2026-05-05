# How to see WoundScan running

This is a step-by-step guide to take the platform from this repository
to a running system you can use. It covers two paths:

- **Path A — local dev** (today, on your laptop): the engine + web
  dashboard running in Docker, the iOS app on your iPhone talking to
  your laptop's IP.
- **Path B — internal pilot** (this/next week, AWS): the engine deployed
  to your AWS account, the web dashboard hosted, the iOS app
  TestFlight-distributed to your three pilot clinicians.

Both paths assume the engine PR (#1) merges first. The PR is fully
green on CI; merge whenever you're ready.

---

## Tooling install (do this once)

### macOS

Install [Homebrew](https://brew.sh) first if you don't have it, then:

```bash
brew install --cask docker
brew install awscli terraform node@20 python@3.11 xcodegen
```

Open Docker Desktop from Applications once and accept the prompts.

For iOS development: install Xcode 15.4+ from the Mac App Store, then:

```bash
sudo xcode-select --install
sudo xcodebuild -license accept
```

### Linux (Ubuntu/Debian)

```bash
# Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER  # log out and back in for this to take effect

# AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
unzip awscliv2.zip && sudo ./aws/install

# Terraform
wget -O- https://apt.releases.hashicorp.com/gpg | \
  sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] \
  https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
  sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install -y terraform

# Node 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip
```

iOS development requires a Mac; not available on Linux.

### Windows

Use WSL2 + Ubuntu and follow the Linux instructions inside WSL:

```powershell
# In PowerShell as Administrator:
wsl --install -d Ubuntu-22.04
```

iOS development requires a Mac.

### Verify

```bash
docker info && \
aws --version && \
terraform --version && \
node --version && \
python3.11 --version && \
echo "✅ all tools ready"
```

### Configure AWS (Path B only)

You need an IAM user with admin rights in your dedicated WoundScan AWS
account. From the AWS Console: IAM → Users → Create user → attach
`AdministratorAccess` policy → Security credentials → Create access key.

```bash
aws configure
# AWS Access Key ID:     <paste>
# AWS Secret Access Key: <paste>
# Default region name:   us-east-1
# Default output format: json

aws sts get-caller-identity   # should print your account ID
```

---

## Path A — local dev (30 minutes)

### Prerequisites

- macOS or Linux laptop with the tooling above installed
- An iPhone 12 Pro or later running iOS 17+ (iOS step only)

### Step 1: Clone and start the engine

```bash
git clone https://github.com/albacetemeddev/woundsare3d.git
cd woundsare3d/woundscan-engine
docker compose up -d
```

This starts:
- Postgres on `:5432`
- Redis on `:6379`
- Engine API on `:8000` (FastAPI, OpenAPI docs at <http://localhost:8000/docs>)
- Celery worker

Verify:

```bash
curl http://localhost:8000/healthz   # {"status":"ok"}
curl http://localhost:8000/version   # {"engine_version":"1.0.0"}
```

### Step 2: Start the web dashboard

```bash
cd ../woundscan-web
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 \
API_URL=http://localhost:8000 \
npm run dev
```

Open <http://localhost:3000>.

Sign in with the dev credentials baked into the engine:
- Email: `dev@local`
- Password: `dev`
- TOTP: `000000`

(These are env-controlled defaults — see `WS_DEV_USER` / `WS_DEV_PASSWORD` /
`WS_DEV_TOTP` in `engine/src/woundscan/api/routes/auth.py`. Override
them via env vars before going to staging.)

You should see the dashboard. The wounds list and trajectory pages will
be empty until the iOS app uploads a measurement.

### Step 3: Build and install the iOS app

```bash
cd ../woundscan-ios
brew install xcodegen
xcodegen generate
open WoundScan.xcodeproj
```

In Xcode:
1. Select the `WoundScan` target → Signing & Capabilities → set your
   development team and a unique bundle ID.
2. Connect your iPhone, select it as the run target.
3. In `WoundScan/App/AppState.swift`, change `apiBaseURL` to your
   laptop's LAN IP (e.g. `http://192.168.1.42:8000`). Make sure your
   laptop and phone are on the same network.
4. Click Run.

In the app:
1. Sign in with `dev@local` / `dev` / `000000`.
2. Tap **Capture**.
3. Print the fiducial sticker (any 5×5 ArUco tag will work for testing —
   we'll ship the canonical sticker PDF separately) and place it next
   to a test object (an apple, an orange, your knee).
4. Hold the iPhone ~30 cm away, wait for the stable-tracking checkmark,
   tap **Capture**, hold steady through the 60-frame burst.
5. Tap probe locations on the photo and enter depths.
6. Confirm the proposed boundary.
7. Watch the result come back.

### Step 4: Verify end-to-end

The dashboard at <http://localhost:3000> should now show:
- The wound under "Wounds"
- The measurement detail with V, SA, CIs, quality grade, graft recs
- The PDF download (renders via ReportLab in the engine)
- The FHIR JSON export

That's the full loop.

---

## Path B — internal pilot deployment (1-2 weeks)

This puts WoundScan in front of your three pilot clinicians using AWS.
You will need PHI-safe infrastructure even for a pilot — there are no
shortcuts here.

### Prerequisites

- All tooling from "Tooling install" above (Docker, AWS CLI, Terraform, Node, Python)
- AWS account **dedicated to WoundScan** (no PHI in shared accounts)
- **Signed BAA with AWS** (Console → Support → Contracts → request BAA;
  takes 1-2 business days to come back)
- AWS CLI configured (`aws configure`, see "Tooling install" above)
- Domain name you control (e.g. `woundscan.albacetemed.com`)
- Apple Developer Program enrollment ($99/yr) for TestFlight distribution

> **Note on working directory**: every command block in Path B starts with
> `cd <repo-root>` so you can copy-paste from any prior shell state.
> `<repo-root>` is the directory containing this `RUNBOOK.md` (where you
> ran `git clone`).

### Step 1: Bootstrap AWS (1-2 days)

```bash
cd <repo-root>/infrastructure/terraform/environments/dev
# First, create the state bucket and lock table out of band:
aws s3api create-bucket --bucket woundscan-tf-state-dev --region us-east-1
aws s3api put-bucket-versioning --bucket woundscan-tf-state-dev \
  --versioning-configuration Status=Enabled
aws dynamodb create-table --table-name woundscan-tf-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# Then seed the secrets:
aws secretsmanager create-secret --name woundscan/dev/db-password \
  --secret-string "$(openssl rand -base64 32)"
aws secretsmanager create-secret --name woundscan/dev/jwt-signing \
  --secret-string "$(openssl rand -base64 64)"

# Then provision the rest:
terraform init
terraform plan -var image=PLACEHOLDER  # review the plan
terraform apply -var image=PLACEHOLDER
```

This builds:
- VPC with private subnets, NAT, flow logs (CloudWatch)
- KMS key with rotation
- S3 artifact bucket (object lock, 30-day retention in dev)
- ECS cluster + task definition (placeholder image)
- IAM roles for the task

Production deployment (`environments/prod`) follows the same flow once
your pilot is satisfied.

### Step 2: Build and push the engine image (30 min)

ECS Fargate runs on `linux/amd64`. If you're building on Apple Silicon
you **must** pass `--platform linux/amd64`, otherwise ECS will fail to
launch with `CannotPullContainerError: image Manifest does not contain
descriptor matching platform 'linux/amd64'`.

```bash
# Build (linux/amd64 is required even on Apple Silicon)
cd <repo-root>/woundscan-engine
docker buildx build --platform linux/amd64 -t woundscan-engine:0.1.0 --load .

# Tag for ECR
aws ecr create-repository --repository-name woundscan-engine
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGION=us-east-1
ECR=$ACCOUNT.dkr.ecr.$REGION.amazonaws.com
docker tag woundscan-engine:0.1.0 $ECR/woundscan-engine:0.1.0

# Push
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin $ECR
docker push $ECR/woundscan-engine:0.1.0

# Seed the DB password secret (Terraform creates the container, you set the value)
aws secretsmanager put-secret-value \
  --secret-id woundscan/dev/db-password \
  --secret-string "$(openssl rand -base64 32)"

# Re-apply Terraform with the real image
cd <repo-root>/infrastructure/terraform/environments/dev
terraform apply -var image=$ECR/woundscan-engine:0.1.0
```

> **Dev has no RDS.** `environments/dev/main.tf` provisions VPC, S3, ECS,
> KMS, and a Secrets Manager *container* for the DB password — but no
> RDS instance. The engine starts cleanly (the DB connection is lazy on
> first request), and `GET /healthz` returns 200, but any endpoint that
> hits the database (auth, wounds, measurements, uploads) will fail
> until you add an RDS module to `dev/main.tf` and wire `WS_DB_HOST`
> into the ECS task definition. For pilot, copy the `module "rds"`
> block from `environments/prod/main.tf`.


ECS will pull the image and start the API. Find the load balancer
hostname in the Terraform output, point your subdomain at it via Route53.

### Step 3: Run database migrations (15 min)

The engine ships with SQLAlchemy models but no Alembic migrations file
yet. Either:

a) **Bootstrap from models** (quick, fine for a pilot):
```bash
# Connect to the RDS endpoint via a one-off ECS task:
aws ecs run-task --cluster woundscan-dev-api \
  --task-definition woundscan-dev-api \
  --overrides '{"containerOverrides":[{"name":"api","command":["python","-c","from woundscan.storage.postgres import Base, create_engine; Base.metadata.create_all(create_engine())"]}]}' \
  --launch-type FARGATE \
  --network-configuration 'awsvpcConfiguration={subnets=[<private-subnet-id>],securityGroups=[<task-sg-id>],assignPublicIp=DISABLED}'
```

b) **Generate Alembic migrations** (better, ~2 hours of work):
```bash
cd <repo-root>/woundscan-engine
alembic init migrations
# Edit migrations/env.py to point at woundscan.storage.postgres.Base.metadata
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
# Commit migrations to the repo; CI will apply them in deploy
```

I recommend option (b) before any data lands in the DB.

### Step 4: Deploy the web dashboard (30 min)

The simplest path: Vercel.

```bash
cd <repo-root>/woundscan-web
npm install -g vercel
vercel login
vercel link
vercel env add NEXT_PUBLIC_API_URL production   # https://api.woundscan.albacetemed.com
vercel env add API_URL production                # same; used in API routes
vercel --prod
```

Vercel handles TLS, CDN, build pipeline. Cost: free tier is fine for
internal pilot. Move to ECS Fargate behind your own ALB if you need
the dashboard inside the same VPC as the engine for VPC peering or
audit reasons.

### Step 5: TestFlight the iOS app (1-2 days, mostly Apple review)

```bash
cd <repo-root>/woundscan-ios
xcodegen generate
# Open in Xcode, set release config to point at your prod API URL
# Product → Archive → Distribute App → App Store Connect → Upload
```

Then in App Store Connect:
1. Create the app record
2. Add internal testers (your three pilot clinicians)
3. Submit the build for TestFlight review (typically 24-48h for first build, faster after)
4. Clinicians install TestFlight on their iPhones, accept the invite, install the app

### Step 6: Provision your three pilot clinicians (1 hour)

Three things per clinician:

1. **Engine user record**: directly insert via psql into the `users`
   table. Each user gets:
   - `id`: UUID
   - `email`: their work email
   - `password_hash`: from `woundscan.auth.identity.hash_password("temporary-password")`
   - `totp_secret_encrypted`: from `woundscan.auth.mfa.generate_totp_secret()`
     — encrypt with KMS before storing
   - `role`: `"clinician"`
   - `organization_id`: your org UUID
2. **TOTP enrollment**: scan the QR code from
   `pyotp.totp.TOTP(secret).provisioning_uri(name="<email>", issuer_name="WoundScan")`
   into Authy or 1Password.
3. **TestFlight invite**: send via App Store Connect.

I'll add a `scripts/seed_user.py` and a self-service enrollment page
in a follow-up — see #TBD.

### Step 7: First clinical capture

Have one of the pilot clinicians:
1. Sign in to the iOS app with their credentials + TOTP
2. Capture a real wound (with patient consent and standard PHI handling)
3. Verify the result lands in the web dashboard
4. Download the PDF, review the methodology section
5. Sign off the measurement

If anything doesn't work, the audit log on the dashboard shows the
exact API call sequence; the structured logs in CloudWatch show the
engine pipeline timing per step.

---

## What you need to do that I can't do for you

In rough order:

1. **Sign the AWS BAA.** Without this, deploying PHI to your AWS
   account is a HIPAA violation.
2. **Get your three pilot clinicians' written agreement** to be early
   testers, plus IRB/ethics clearance if your jurisdiction requires it
   for clinical decision support.
3. **Print the fiducial sticker.** I'll generate a canonical PDF in a
   follow-up; for now, any 5×5 ArUco DICT_5X5_50 marker at a known size
   (say 10mm) is fine for testing. There are free generators online.
4. **Apple Developer enrollment + the three pilot clinicians' Apple IDs**
   for TestFlight.
5. **Domain + ACM certificate** for the API hostname.
6. **Phantom procurement** (deferred but on the critical path for
   regulatory): silicone wound phantoms with known geometry. ATS
   Laboratories and CIRS sell them; budget ~$8-15k for a 12-phantom set.
7. **Saline cross-check protocol**: the dashboard already has the entry
   form — your clinicians need to know to use it, with a documented
   procedure (e.g. "after each capture, instill 5mL saline and record
   actual displacement").
8. **Pen-test booking** (annual requirement; not blocking pilot but
   blocking commercial use).

## What I'll add in follow-ups

These are tracked in GitHub issues:

- **#2** — engine coverage 72% → 90% (test infrastructure: moto,
  testcontainers, ArUco fixtures, PDF goldens)
- New: clinician seeding script + self-service TOTP enrollment page
- New: Alembic migrations
- New: canonical fiducial sticker PDF
- New: production Terraform environment (`environments/prod`) with
  cross-region S3 replication, multi-AZ everything, GuardDuty, Security Hub
- New: incident runbook + on-call rotation docs
- New: clinician training materials (1-pager + 5-min video)

## Operational FAQs

**Q: How do I know it's working in production?**
A: CloudWatch alarms fire on:
- API 5xx >1% over 5 min
- Pipeline duration P95 >5s
- Quality F-grade rate >25% over 1h
- DB connection pool exhaustion
The Prometheus `/metrics` endpoint exposes `woundscan_measurements_total`,
`woundscan_quality_grade_total`, `woundscan_fusion_duration_seconds`.
Wire these to Grafana or CloudWatch dashboards.

**Q: How do I verify the math is still correct after a deploy?**
A: The synthetic + property + benchmark suites run on every PR. If
they regress, CI blocks merge. Plus the `regulatory` workflow checks
that every requirement in `docs/regulatory_traceability.md` is mapped
to a passing test.

**Q: Where is PHI stored?**
A: In RDS Postgres, encrypted at rest with KMS, with column-level
encryption on PII columns. Binary capture artifacts are in S3 with
object lock and the same KMS key. Audit logs in Postgres + tamper-
evident hash chain. Never in application logs (we use structlog with
PHI fields redacted).

**Q: How do I rotate a clinician out?**
A: Set `is_active = false` on their `users` row. JWT becomes invalid
within the 15-minute idle timeout window. Their TestFlight access can
be revoked in App Store Connect.

**Q: What if the engine answers wrong?**
A: Every measurement carries full provenance: engine version, model
versions and content hashes, input hashes, intermediate hashes,
processing duration. Open `<measurement_id>.pdf` and the last page
shows the full chain. Reproduce via:
```bash
woundscan-debug replay <measurement_id>
```
(this CLI doesn't exist yet but is straightforward to add — the
provenance JSON has everything needed to re-run).
