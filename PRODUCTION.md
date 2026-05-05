# WoundScan production readiness

What still has to happen for this to be a real production app instead
of a TestFlight build pointed at localhost.

## 1. Backend deployment (engine + Postgres + Redis + S3)

Terraform already exists at `infrastructure/terraform/environments/dev/`.
The dev env was partially applied (ACM cert + ALB + ECS task def);
RDS and the actual ECS service still need to be brought up.

Steps:

1. Set `AWS_PROFILE` (or `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`)
   to a profile that has admin in the WoundScan AWS account.
2. `cd infrastructure/terraform/environments/dev && terraform init`.
3. `terraform plan -out=plan.out` — review carefully. Expect to see:
   - VPC + subnets
   - RDS Postgres 15
   - ElastiCache Redis
   - ECS cluster + service for `woundscan-engine` (FastAPI)
   - ECS service for `woundscan-engine-worker` (Celery)
   - ALB with TLS termination on `woundscan.albacetemeddev.com`
     (ACM cert exists; HTTPS listener needs to be enabled)
   - S3 bucket for mesh artefacts
4. `terraform apply plan.out`. ~15 min.
5. Run the one-off DB schema bootstrap (Alembic migrations don't exist
   yet — current path is `Base.metadata.create_all`):
   ```bash
   aws ecs run-task ... --command="python -c 'from woundscan.storage.postgres import Base, create_engine; Base.metadata.create_all(create_engine())'"
   ```
6. Seed the first real clinician account (replaces the dev backdoor):
   - Generate a TOTP secret: `python -c "import pyotp; print(pyotp.random_base32())"`.
   - INSERT a `users` row with `bcrypt(password)` and the TOTP secret.
   - Hand the secret to the clinician via secure channel; they pair it
     in their TOTP app.
7. **Set `WS_ALLOW_DEV_LOGIN` to `0` (or omit)** in the prod task
   definition. The auth handler now refuses the dev backdoor unless
   that flag is explicitly `1` — leaving it unset is the safe default.

Approx. monthly cost on dev sizing: $110–140 (single t4g.small ECS,
db.t4g.small RDS, t4g.micro Redis, ALB, NAT gateway).

## 2. Web portal hosting

The portal is plain Next 14, deploys clean to Vercel.

Steps:

1. `cd woundscan-web && vercel link` (one-time, picks the AlbaceteMedDev
   team).
2. Set env vars in the Vercel dashboard (or via CLI):
   ```
   NEXT_PUBLIC_API_URL=https://woundscan.albacetemeddev.com
   API_URL=https://woundscan.albacetemeddev.com
   ```
3. `vercel --prod`.
4. Add a custom domain, e.g. `portal.albacetemeddev.com` →
   Vercel project. DNS via your existing host.

After this:
- The desktop portal is live at the public URL.
- The iOS app's `AppState.portalURL` automatically resolves to the
  prod portal because `apiBaseURL.host == "woundscan.albacetemeddev.com"`
  → strips the `api.` prefix (or just keeps the host as the portal
  origin if you serve the portal from the same domain).

## 3. iOS App Store submission

Build 8 is in TestFlight. To go from TestFlight to the App Store:

### a. Clear the "detail not found" error

That's App Store Connect saying "you have a build but no App Store
*version* to attach it to." Fix:

1. App Store Connect → My Apps → WoundScan → **App Store** tab (not
   TestFlight).
2. iOS App version `1.0` shows as missing. Fill out:
   - **App description** — see draft below.
   - **Keywords** — `wound, ulcer, DFU, pressure injury, clinical, podiatry`.
   - **Support URL** — `https://albacetemeddev.com/support` (create
     this page on the marketing site).
   - **Marketing URL** (optional) — `https://albacetemeddev.com`.
   - **Privacy policy URL** — required for medical apps; create a
     HIPAA-aware page on albacetemeddev.com first.
   - **Category** — Medical (primary). Health & Fitness (secondary).
   - **Age rating** — 17+ (medical content).
   - **Copyright** — `© 2026 Albacete MedDev LLC`.
   - **Screenshots** — 6.7" iPhone (1290×2796): at least 3.
     5.5" iPhone (1242×2208): at least 3.
   - **App Privacy** disclosure (Data Used to Track You / Data Linked
     to You / Data Not Linked to You) — see draft below.
3. Click **+ Add Build** under the version, pick build 8.
4. Submit for review.

### b. Draft App Store description

```
WoundScan brings clinical-grade wound measurement to the bedside
with the iPhone’s LiDAR sensor.

Capture a 60-frame ARKit burst, get back surface area, volume, max
depth, perimeter, tissue composition, and a healing trajectory — all
in seconds, all auditable, all linked to a HIPAA-aware provider portal.

KEY FEATURES
• 3D wound capture with LiDAR + ARKit
• Volume, surface area, depth with 95% confidence intervals
• Quality scoring and motion / lighting guidance
• Provider portal: patient roster, claims, compliance, reports
• UDI-traceable graft tracking and Medicare reimbursement estimator
• Audit-safe note templates with SHA-256 hashing on sign

WoundScan is clinical decision support — not a diagnostic device.
The clinician retains decision authority.

For credentialed clinicians only. Requires an iPhone with a LiDAR
sensor (iPhone 12 Pro or newer).
```

### c. Draft App Privacy disclosure

- **Data Linked to You** (used by the app):
  - Health & Fitness → wound measurements, photos
  - Identifiers → user ID
  - Sensitive info → photos may show body parts
- **Data Used to Track You**: none.
- **Data Not Linked to You**: device identifiers (crash logs).
- **Third-Party SDKs**: none currently.

## 4. iOS production env switch

The iOS app's default API base URL is already
`https://woundscan.albacetemeddev.com` (set in `AppState.swift`).
That URL is what the prod build uses. The dev override
(`WS_API_BASE_URL` Info.plist key) is unset, so prod points at prod
automatically. **No iOS code changes needed once the backend is up.**

## 5. Production-only cleanup

- [ ] `sample.ts` is fine — only used by `(portal)/*` tab pages for
      the demo skeleton; real data flows in via the engine endpoints.
      Once real wounds exist, the demo data is invisible. To remove it
      entirely, replace each tab with engine-fetched data.
- [x] Dev login backdoor (`dev@local / dev / 000000`) now requires
      `WS_ALLOW_DEV_LOGIN=1`. Production ECS task def must NOT set it.
- [ ] `WS_JWT_SIGNING_KEY` in `docker-compose.yml` is "dev-only";
      production must use an AWS Secrets Manager-backed value.
- [ ] Remove the loose `Picture*.png`, `Mock Portal.png`, etc. from
      the repo root once the marketing site has them.
- [ ] Add Alembic migrations so prod DB upgrades are reproducible.
- [ ] CloudWatch alarms on engine 5xx rate, RDS CPU, ALB target
      health.

## 6. What I need from you to actually deploy

- [ ] AWS credentials (profile name + confirm I should run
      `terraform apply` on the dev/prod env)
- [ ] Vercel team + project name (or "create new")
- [ ] DNS control for `albacetemeddev.com` (Cloudflare? Route 53?
      somewhere else?) so I can point `portal.` and verify ACM
- [ ] Privacy-policy URL + Support URL — or permission to draft both
      and get them onto your marketing site
- [ ] iPhone screenshots for App Store (or screenshare-and-script
      session where I drive a simulator and you approve)

Tick the boxes you want me to handle and we'll move.
