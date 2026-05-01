# WoundScan

Medical-grade 3D wound measurement platform: iPhone capture, sensor
fusion, machine learning, full provenance, designed to support FDA
510(k) submission without rewrite.

## Repository layout

```
WoundsAre3D/
├── woundscan-engine/     Python FastAPI engine + math + ML
├── woundscan-ios/        SwiftUI + ARKit iPhone capture app
├── woundscan-web/        Next.js dashboard for review and admin
├── infrastructure/       Terraform, Docker, deployment scripts
└── .github/workflows/    CI/CD pipelines
```

Each subproject is self-contained with its own README.

## Initial deployment

Internal use across our distribution network. Operates under the 21st
Century Cures Act § 3060 clinical decision support exemption — clinician
retains decision authority, no diagnostic claims, methodology
transparently displayed in every report.

## Eventual deployment

Commercial sale post-510(k) clearance. Architecture supports FDA
submission without rewrite:
- Bidirectional regulatory traceability matrix (`woundscan-engine/docs/regulatory_traceability.md`)
- Versioned algorithms (confidence weights, force correction tables, ML weights)
- Tamper-evident audit chain
- Per-measurement provenance with content-hashed inputs
- Comprehensive validation harness (synthetic + property + phantom + clinical)

## Quick start (engine)

```bash
cd woundscan-engine
pip install -e ".[dev]"
pytest                  # 176+ tests
docker compose up -d    # Postgres + Redis + API
woundscan-api           # API on :8000
```

## Quick start (web)

```bash
cd woundscan-web
npm install
npm run dev             # http://localhost:3000
```

## Quick start (iOS)

```bash
cd woundscan-ios
brew install xcodegen
xcodegen generate
open WoundScan.xcodeproj
```

Requires iPhone 12 Pro or later (LiDAR sensor) running iOS 17+.

## Build status

| Component | CI |
|---|---|
| Engine | `.github/workflows/engine-ci.yml` |
| Web | `.github/workflows/web-ci.yml` |
| iOS | `.github/workflows/ios-ci.yml` |
| Regulatory | `.github/workflows/regulatory.yml` |

## What's in the box

### Engine
- 13 subpackages: api, auth, capture, fusion, geometry, graft, ml,
  monitoring, output, quality, storage, synthesis, validation
- 176+ tests (unit, integration, regulatory, benchmarks)
- Heteroscedastic GP fusion with Monte Carlo uncertainty
- Six layers of validation (synthetic, properties, benchmarks, phantom,
  clinical, regulatory)
- HIPAA-grade auth + audit + tamper-evident hash chain
- FastAPI service with full OpenAPI spec
- Celery worker for async heavy fusion jobs
- Full PDF / CSV / FHIR export with provenance

### iOS app
- ARKit + LiDAR + AVFoundation capture pipeline
- Multi-frame burst (60 frames in 4 seconds)
- Live motion + fiducial feedback
- Probe entry with auto-detect + manual fallback
- Boundary annotation with ML proposal
- Offline queue with retry
- 15-minute idle session timeout

### Web dashboard
- Auth with TOTP MFA
- Wound trajectory charts (volume, SA, depth)
- Phantom calibration submission
- Admin: products, audit log, ML metrics
- All security headers (HSTS, CSP, etc.)

### Infrastructure
- Terraform for AWS HIPAA-compliant deployment
- VPC with private subnets + flow logs
- ECS Fargate with autoscaling
- RDS Postgres with encryption + multi-AZ
- S3 with object lock (6-year retention)
- KMS-managed encryption keys with rotation
- CloudWatch + GuardDuty + Security Hub

## Disclaimer

For clinical decision support only. Not for diagnostic use. Clinician
retains decision authority. Methodology disclosed in every measurement
report.
