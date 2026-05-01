# WoundScan — Maximum Accuracy Production Build

> Build target: best-in-class measurement accuracy, deployed for internal
> use under clinical decision support carve-out, with every architectural
> choice made to support eventual FDA 510(k) submission without rewrite.
> Realistic timeline: 3–4 months of focused work.

---

## What we're building

A medical-grade 3D wound measurement platform that produces
sub-2%-accuracy volume, surface area, and skin substitute graft sizing
under real-world clinical conditions. Multi-modal sensor fusion of iPhone
LiDAR, RGB photography, and clinician-entered probe measurements, with
machine learning for boundary segmentation and tissue classification,
Gaussian process fusion with uncertainty quantification, and full provenance
tracking on every output.

Initial deployment: internal use across our distribution network. Operates
under the 21st Century Cures Act § 3060 clinical decision support
exemption — clinician retains decision authority, no diagnostic claims,
methodology transparently displayed.

Eventual deployment: commercial sale post-510(k) clearance. All code
written to that bar from day one.

---

## Three deliverables

1. **Engine** — Python service with math, ML, fusion, reports
2. **iOS app** — SwiftUI + ARKit, full capture pipeline
3. **Dashboard** — Next.js web app for review and analytics

Plus infrastructure: AWS HIPAA-compliant deployment, CI/CD, validation
test harness, documentation suite ready for regulatory submission.

---

## Engine architecture

### Stack
- Python 3.11
- FastAPI for HTTP API
- numpy, scipy, scikit-image, opencv-python for math
- GPy or GPyTorch for Gaussian process regression
- PyTorch for ML models (segmentation, classification)
- Pydantic for data models with strict validation
- structlog for structured logging
- pytest, hypothesis, pytest-benchmark for testing
- ReportLab for PDF generation
- PostgreSQL with row-level security for data
- S3 with object lock for scan files (tamper-evidence)
- Redis for job queue (long-running fusion tasks)
- Celery for async processing

### Project structure
```
woundscan-engine/
├── pyproject.toml
├── docker-compose.yml
├── Dockerfile
├── README.md
├── docs/
│   ├── architecture.md
│   ├── math_reference.md
│   ├── ml_models.md
│   ├── validation_protocol.md
│   ├── regulatory_traceability.md
│   └── deployment.md
├── src/woundscan/
│   ├── api/
│   │   ├── routes/
│   │   ├── auth.py
│   │   └── audit.py
│   ├── capture/
│   │   ├── depth_map.py        # iPhone LiDAR ingestion
│   │   ├── point_cloud.py      # PLY processing
│   │   ├── photo.py            # RGB image handling
│   │   ├── fiducial.py         # ArUco/checkerboard detection
│   │   ├── multiframe.py       # temporal averaging across frames
│   │   ├── polarization.py     # cross-polarized image support
│   │   ├── multispectral.py    # IR/multispectral support
│   │   └── probe.py            # physical measurement ingestion
│   ├── quality/
│   │   ├── specularity.py
│   │   ├── texture.py
│   │   ├── lighting.py
│   │   ├── motion.py
│   │   ├── edge_proximity.py
│   │   ├── frame_consistency.py
│   │   └── confidence.py       # composite confidence map
│   ├── ml/
│   │   ├── boundary_segmentation.py  # U-Net wound boundary
│   │   ├── tissue_classification.py  # granulation/slough/eschar/etc
│   │   ├── probe_detection.py        # auto-detect probe tip in photos
│   │   ├── fiducial_robust.py        # robust to occlusion/angle
│   │   └── models/                   # weight files, model versioning
│   ├── fusion/
│   │   ├── interpolation.py         # thin-plate spline
│   │   ├── gaussian_process.py      # heteroscedastic GP (primary)
│   │   ├── bundle_adjustment.py     # multi-view joint optimization
│   │   ├── temporal.py              # Kalman filter across visits
│   │   └── force_correction.py      # probe compression compensation
│   ├── geometry/
│   │   ├── surface_area.py          # 3D gradient integral
│   │   ├── volume.py                # Simpson's rule
│   │   ├── perimeter.py
│   │   ├── undermining.py
│   │   ├── uncertainty.py           # confidence intervals on outputs
│   │   └── shape_descriptors.py     # circularity, irregularity metrics
│   ├── graft/
│   │   ├── sizing.py
│   │   ├── product_db.py            # IFU overlap database
│   │   └── recommendation.py        # product selection logic
│   ├── validation/
│   │   ├── consistency.py           # camera vs probe agreement
│   │   ├── plausibility.py          # geometric sanity checks
│   │   ├── temporal_plausibility.py # cross-visit reasonableness
│   │   ├── quality_score.py         # A/B/C/F grading
│   │   └── phantom_calibration.py   # silicone phantom validation
│   ├── synthesis/
│   │   ├── analytic_shapes.py       # hemisphere, ellipsoid, etc
│   │   ├── irregular_beds.py        # Perlin/Simplex noise
│   │   ├── clinical_morphologies.py # DFU, VLU, pressure stages, etc
│   │   ├── degradation.py           # add realistic noise/artifacts
│   │   └── ground_truth.py          # analytic V and SA computation
│   ├── output/
│   │   ├── pdf_report.py
│   │   ├── csv_export.py
│   │   ├── fhir_export.py           # ready for EHR integration later
│   │   ├── trajectory_plot.py
│   │   └── provenance.py            # full audit chain on every output
│   ├── storage/
│   │   ├── postgres.py
│   │   ├── s3.py
│   │   └── tamper_evidence.py       # cryptographic hashes, object lock
│   ├── auth/
│   │   ├── identity.py
│   │   ├── mfa.py
│   │   ├── sessions.py
│   │   ├── rbac.py                  # clinician/reviewer/admin roles
│   │   └── audit_log.py             # HIPAA access logging
│   └── monitoring/
│       ├── metrics.py
│       ├── tracing.py
│       └── error_reporting.py
└── tests/
    ├── unit/
    ├── integration/
    ├── regulatory/                  # 510(k)-ready validation tests
    ├── benchmarks/                  # accuracy regression tracking
    └── fixtures/
        ├── synthetic_wounds/
        ├── phantom_scans/
        └── clinical_samples/
```

---

## Core math (must be implemented exactly)

### Per-pixel confidence map
```
c(x, y) = 0.25·(1 - specularity)
        + 0.20·texture_contrast
        + 0.15·lighting_uniformity
        + 0.15·(1 - motion_artifact)
        + 0.10·edge_distance
        + 0.10·frame_consistency
        + 0.05·boundary_confidence (from ML segmentation)
```

Each component normalized to [0, 1]. Weights are tunable via config but
must be documented and version-locked.

### Heteroscedastic Gaussian process fusion

Given physical probe measurements P = {(x_i, y_i, d_i, σ_phys_i)} and
camera depth field d_cam(x, y) with confidence c(x, y), find the posterior
distribution over true depth surface d_true(x, y).

Kernel: Matérn 5/2 with separate length scales per dimension, learned
from data. Noise model: σ_phys for probe points (typically 0.5–1.0mm
depending on probe type), σ_cam(x, y) = σ_base / max(c(x, y), 0.05) for
camera points where σ_base is estimated from frame-to-frame consistency.

Output: posterior mean d_fused(x, y) AND posterior covariance K(x, y; x', y').
The covariance is what enables confidence intervals on volume and surface
area downstream.

Implementation: GPyTorch with sparse approximations for scaling. Inducing
point selection via greedy variance reduction. Kernel hyperparameters
optimized per measurement via marginal likelihood maximization.

### Multi-view bundle adjustment

When the iOS app captures multiple scans of the same wound in a session
(different angles), jointly optimize:
- Camera poses for each capture
- Single coherent depth surface

Standard photogrammetry formulation, Levenberg-Marquardt optimization.
Use OpenCV's bundle adjustment as starting point, customize loss function
to incorporate fiducial constraints and probe-point anchors.

### Bayesian temporal fusion (cross-visit)

Each new measurement updates a state estimate using Kalman filtering:
```
x_t = F·x_{t-1} + w_t       (state transition: wounds heal continuously)
z_t = H·x_t + v_t            (observation: current measurement)
```

State vector includes volume, surface area, max depth, and their rates of
change. Process noise reflects expected healing rates from wound type.
Observation noise comes from the GP posterior covariance.

Output: filtered estimate of current state with uncertainty, plus
flagging of outlier measurements that disagree with the temporal model.

### Force-correction for probe compression

Empirically derived correction:
```
d_true = d_measured - α(tissue_type) · f(force_category)
```

where α depends on tissue type (granulation: 1.2mm at firm pressure,
fibrous: 0.4mm at firm pressure, etc.) and f is a piecewise function
mapping the clinician's categorical force input (light/medium/firm) to
correction magnitude. Coefficients calibrated on phantom measurements
during development and refined from saline cross-checks in deployment.

### 3D surface area with uncertainty
```
S_3D = ∫∫ √(1 + (∂d/∂x)² + (∂d/∂y)²) dA

σ²_S_3D = computed via Monte Carlo sampling from the GP posterior
        (1000 samples, integrate each, report mean and 95% CI)
```

### Volume with uncertainty
```
V = ∫∫ d(x, y) dA
σ²_V = analogous Monte Carlo from GP posterior
```

### Graft sizing with uncertainty
```
A_graft = S_3D + 2δ·P_eff + 4δ²

A_graft_recommended = mean(A_graft) + 2·std(A_graft)
```
The recommendation uses 2-sigma upper bound to ensure adequate coverage
under measurement uncertainty. Methodology disclosed in report.

### Quality grade

Composite A/B/C/F based on:
- Mean confidence across wound bed
- Number and quality of physical anchor points
- Camera-probe agreement at anchor locations
- Fiducial detection success and pose error
- Photo quality metrics (resolution, focus, exposure)
- Frame consistency (motion stability)
- ML segmentation confidence

Detailed breakdown attached to every measurement.

---

## ML models

Three models, all trained from scratch on a labeled dataset we build:

### 1. Wound boundary segmentation (U-Net)
Input: RGB photo (1024x1024 crop). Output: binary mask of wound vs
periwound. Training: start with publicly available wound datasets
(Medetec, FUSC, AZH wound database), augment with our internal
captures as we accumulate them.

### 2. Tissue type classification (per-pixel)
Input: RGB photo + depth map. Output: per-pixel class probabilities for
{granulation, slough, eschar, epithelial, bone/tendon, periwound}.
Architecture: U-Net++ or DeepLabV3 with multi-channel input.

### 3. Probe tip detection (object detection)
Input: RGB photo. Output: bounding box and tip position of probe in image
when present. YOLOv8 nano, fine-tuned on photos with various probe types
(cotton-tipped applicators, plastic gauges, Kundin gauges).

All models versioned with model card (training data, performance metrics,
known failure modes), weight files content-hashed, model version recorded
in every measurement's provenance.

---

## Capture pipeline (iOS app)

### Multi-modal capture in a single session
1. Login with credentials + MFA
2. Select patient (token-based, no PHI cached locally)
3. Select or create wound
4. Print fiducial sticker (4 ArUco markers around a known-size square),
   place adjacent to wound
5. Primary capture: 60-frame burst over 4 seconds at native resolution
   - Depth + RGB + ARKit pose for each frame
   - Real-time fiducial detection with green-light feedback
   - Live confidence meter shown to clinician
6. Optional secondary captures from different angles (system computes
   bundle adjustment automatically)
7. Optional polarized capture if polarizer attachment present
8. Optional multispectral via Face ID IR sensor
9. Probe measurements:
   - System auto-detects probe tip in photos when probe is visible
   - Manual tap-on-photo fallback for points where probe wasn't visible
   - Clinician enters depth + force category (light/medium/firm)
   - Minimum 5 points, recommend 9, support up to 25
10. Wound boundary annotation:
    - ML proposes boundary
    - Clinician edits if needed
    - Final boundary serialized as polygon in mm coordinates
11. Product selection (auto-fills overlap from product database)
12. Upload to engine, await result
13. Display result with confidence intervals, quality grade, recommendation
14. Generate and review PDF
15. Sign off, commit to record

### Key UX principles
- Every screen shows the clinician what the system "thinks" and lets them
  override
- Confidence intervals shown alongside point estimates always
- Quality grade visible before sign-off; F-grade requires explicit
  acknowledgment and recapture recommendation
- Methodology accessible via "How was this calculated?" link on every
  result
- Offline-capable: capture works without network, queues for upload

---

## Web dashboard

### Stack
- Next.js 14, TypeScript, Tailwind, shadcn/ui
- Recharts for trajectory analytics
- React-PDF for in-browser report viewing

### Pages and features
- Login + MFA
- Dashboard with filters (clinician, date range, wound type, quality grade)
- Wound detail page: timeline of measurements, photo carousel, trajectory
  charts (volume, surface area, depth over time), product applications log
- Measurement detail: all inputs, all outputs, full provenance, downloadable
  PDF, confidence map visualization, depth map visualization
- Patient summary (under deidentified token)
- Audit log access (admin only)
- Product database management (admin only)
- ML model performance dashboard (admin only): tracks segmentation accuracy,
  classification accuracy, drift detection
- Saline cross-check submission form: clinicians can log instillation
  volumes when performed; system uses these to refine error model
- Phantom calibration tracking: monthly phantom scans by each clinician,
  drift alerts when accuracy degrades

---

## Validation harness (regulatory-grade)

### Synthetic wound test suite
Runs on every commit. Must pass:
- Hemisphere (radii 0.5–5cm): V error <0.5%, SA error <0.5%
- Ellipsoidal bowl (various aspect ratios): V error <1%, SA error <1.5%
- Truncated cone, hemicylinder: V error <1%, SA error <2%
- Perlin-noise irregular bed: V error <3%, SA error <5%
- All confidence intervals contain ground truth ≥95% of the time

### Phantom test suite
Runs on every release. Silicone wound phantoms with known geometry
measured by gold-standard methods (caliper for openings, water
displacement for volume, optical scanning for surface area).
- Phantom library: 12 phantoms covering DFU, VLU, pressure injury stages,
  surgical wounds, with varied tissue color, moisture simulation, and
  geometric irregularity
- Field condition tests: phantoms scanned under varied lighting (200-1000
  lux), with simulated exudate (water spray), at varied angles
- Pass criterion: <2% volume error, <3% surface area error in field
  conditions, <1% in ideal conditions

### Clinical correlation studies
Built into the deployment from day one — every measurement that has a
saline instillation cross-check feeds into the validation database.
Continuous monitoring of system error vs ground truth, drift detection,
automatic flagging of model performance regression.

### Property-based testing
Hypothesis library tests for invariants:
- Translation invariance (shifting the wound coordinate system doesn't
  change volume or surface area)
- Rotation invariance
- Scale equivariance (doubling all linear dimensions multiplies volume
  by 8 and surface area by 4)
- Monotonicity (deeper depth at any point increases or maintains volume)
- Confidence interval calibration (95% CIs contain ground truth ≥95%)

### Regulatory traceability
- Every requirement → at least one test
- Every test → at least one requirement
- Documented in `docs/regulatory_traceability.md` with bidirectional links
- Test failures are not just CI failures — they're regulatory deviations
  that get logged in a quality system

---

## HIPAA infrastructure (non-negotiable)

### AWS setup
- BAA signed before any PHI touches the system
- VPC with private subnets, no direct internet exposure
- ECS Fargate for engine, autoscaling 1-10 tasks
- RDS Postgres with encryption, automated backups, point-in-time recovery
- S3 with bucket encryption, versioning, object lock for tamper-evidence
- Secrets in AWS Secrets Manager, rotated quarterly
- TLS 1.3 everywhere, no TLS 1.2 fallback
- WAF in front of public endpoints
- GuardDuty + Security Hub enabled
- CloudTrail with log integrity validation

### Application-level
- All PHI encrypted at rest (column-level encryption for PII)
- All PHI encrypted in transit
- MFA mandatory for all users
- 15-minute idle session timeout
- Role-based access control: clinician sees own patients, reviewer sees
  all in their org, admin sees system but not PHI without elevation
- Comprehensive audit log: every access, every data view, every export,
  every modification, retained 6 years minimum
- No PHI in application logs, ever (use opaque tokens)
- Quarterly access review with deprovisioning workflow
- Annual penetration test
- Incident response plan documented

### Documentation requirements
- Privacy impact assessment
- Data flow diagrams showing all PHI paths
- Risk analysis per HIPAA Security Rule § 164.308
- Backup and disaster recovery plan
- Business continuity plan
- Workforce training records
- Sanction policy for violations

---

## Coding standards

- Python: black, ruff (all checks), mypy strict, 100% type hints
- Swift: SwiftLint with strict rules, SwiftFormat
- TypeScript: ESLint strict, Prettier, no `any` types
- Test coverage: ≥90% on math and ML modules, ≥80% overall
- All code reviewed before merge (Claude Code as reviewer for solo work
  is acceptable but not sufficient — get a second human reviewer for
  the math modules at minimum)
- No silent failures — typed exceptions with diagnostic messages
- All clinical outputs include provenance: engine version, model versions,
  input hashes, intermediate computation hashes, timestamp, processing
  duration
- All numerical inputs validated for unit and range with custom Pydantic
  validators
- Logging via structlog with bound context (no PHI ever)
- Performance budgets: API responses <500ms (excluding fusion compute),
  full measurement processing <30 seconds, PDF generation <5 seconds

---

## Build order

This is a critical path. Each step gates the next. Do not skip.

### Foundation (weeks 1–3)
1. Project scaffolding (engine, iOS, web), Docker, CI/CD setup
2. Synthetic wound generators with analytic ground truth, full test suite
3. Geometry math (surface area, volume, perimeter) validated to <1% on
   analytic shapes
4. Quality components (specularity, texture, lighting, edge, motion,
   frame consistency) with unit tests
5. Composite confidence map with synthetic test cases

### Fusion (weeks 4–5)
6. Thin-plate spline interpolation through physical points
7. Gaussian process fusion with heteroscedastic noise
8. Uncertainty quantification (Monte Carlo CIs on volume and SA)
9. Force correction for probe compression
10. Validation: GP fusion on synthetic wounds with realistic noise,
    confirm <2% error and calibrated CIs

### ML (weeks 5–7)
11. Wound boundary segmentation U-Net, trained on public datasets
12. Tissue type classification, trained on public datasets
13. Probe tip detection, trained on synthetic + collected images
14. Model evaluation, drift detection infrastructure

### API and storage (weeks 6–7)
15. FastAPI endpoints, Postgres schema, S3 integration
16. Auth, MFA, RBAC, audit logging
17. PDF report generation with full provenance
18. CSV and FHIR export

### iOS app (weeks 8–11)
19. Project scaffolding, ARKit integration
20. Capture pipeline (depth, photo, fiducial)
21. Multi-frame averaging, multi-view support
22. Probe entry UI (auto-detect + manual fallback)
23. Boundary annotation UI with ML proposal
24. Upload, result display, PDF preview
25. Offline mode, queue management

### Web dashboard (weeks 9–11)
26. Next.js scaffolding, auth integration
27. Wound list, detail, trajectory pages
28. Admin pages (products, audit log, ML metrics)
29. Saline cross-check entry, phantom calibration tracking

### Infrastructure (weeks 11–12)
30. AWS HIPAA-compliant deployment (VPC, ECS, RDS, S3, WAF)
31. CloudTrail, GuardDuty, Security Hub
32. Monitoring, alerting, runbooks
33. Backup and DR procedures tested

### Validation (weeks 12–13)
34. Phantom library acquisition or fabrication
35. Bench validation on phantom library
36. Documentation suite (architecture, math, ML, validation, regulatory
    traceability, deployment)

### Internal pilot (weeks 13–16)
37. Pilot with 3 clinicians, daily feedback loop
38. Bug fixes and UX iteration
39. Full network rollout
40. Continuous accuracy monitoring in production

---

## What we are explicitly NOT pursuing yet (but could later)

- FDA 510(k) submission (defer until product-market fit; code stays ready)
- Multi-tenant SaaS (single deployment for our network only)
- Direct EHR integration via FHIR (export only; integrations come later)
- Android app (iOS only initially)
- Real-time on-device processing (server compute only)
- Custom hardware (polarizer, tracked probe, force-sensing probe) —
  software supports them when present, but we don't manufacture them
- International deployment (US only initially)

These are deferred but not blocked. The architecture supports them all.

---

## First task

Begin with project scaffolding for the engine:

1. Create the directory structure exactly as specified
2. Write `pyproject.toml` with all dependencies pinned
3. Write `Dockerfile` and `docker-compose.yml` for local development
   (engine + Postgres + Redis)
4. Write `README.md` describing the system, with sections for: overview,
   architecture, getting started, running tests, deployment
5. Set up CI/CD scaffolding (GitHub Actions) with lint, type check, test,
   coverage, security scan jobs

Then move to the synthetic wound generator and validation:

6. Implement `synthesis/analytic_shapes.py` with hemisphere, ellipsoidal
   bowl, truncated cone, hemicylinder generators, each producing depth
   field and analytic ground truth (V, SA, perimeter)
7. Implement `synthesis/irregular_beds.py` with Perlin/Simplex noise on
   top of base shapes
8. Implement `synthesis/clinical_morphologies.py` with shape templates
   for DFU, VLU, pressure stages 2/3/4, surgical dehiscence, traumatic
9. Implement `synthesis/degradation.py` to add realistic noise, motion
   artifacts, specularity simulation, lighting variation
10. Write the test suite that verifies analytic ground truth math is
    correct
11. Implement `geometry/surface_area.py` and `geometry/volume.py` and
    show they recover ground truth from synthetic generators to <1% error
    on analytic shapes, <3% on irregular beds

Stop after step 11 and report back. We validate the foundation before
building on it. This is the most important step in the entire project —
if the math is wrong here, every accuracy claim downstream is wrong.

Do not begin step 12 (Gaussian process fusion) until the foundation is
verified.
