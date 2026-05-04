# WoundScan Engine

A medical-grade 3D wound measurement engine: sensor fusion of iPhone
LiDAR + RGB photography + clinician probe measurements, machine learning
for boundary segmentation and tissue classification, Gaussian process
fusion with uncertainty quantification, and full provenance tracking.

Initial deployment: internal use under the 21st Century Cures Act § 3060
clinical decision support exemption. Eventual deployment: commercial sale
post-510(k) clearance. All code is written to that bar from day one.

## Architecture

```
src/woundscan/
├── api/         FastAPI service + pipeline orchestration + Celery worker
├── auth/        Identity, MFA, sessions, RBAC, audit logging
├── capture/     Multi-modal sensor data ingestion
├── fusion/      GP, TPS, bundle adjustment, Kalman, force correction
├── geometry/    Volume, surface area, perimeter, undermining, uncertainty
├── graft/       Sizing, product database, recommendation
├── ml/          Boundary, tissue, probe, fiducial models (PyTorch)
├── monitoring/  Metrics (Prometheus), tracing (OTel), error reporting
├── output/      PDF, CSV, FHIR, trajectory plots, provenance
├── quality/     Per-pixel and aggregate confidence components
├── storage/     Postgres + S3 + tamper-evident hash chain
├── synthesis/   Synthetic wound generators for validation/training
└── validation/  Consistency, plausibility, quality grade, phantom calibration
```

See `docs/architecture.md` for module dependencies and data flow.

## Getting started

### Local dev

```bash
pip install -e ".[dev]"
docker compose up -d  # Postgres + Redis
woundscan-api          # API on :8000
```

### Run the test suite

```bash
pytest tests/                    # all tests
pytest -m regulatory             # 510(k)-grade validation only
pytest -m benchmark              # accuracy regression
pytest tests/integration/        # FastAPI end-to-end
```

There are 176+ tests today, covering math, fusion, ML, validation,
graft sizing, output generation, auth, storage tamper-evidence, the
full pipeline, and the FastAPI surface.

### Type check & lint

```bash
ruff check src/
black --check src/
mypy src/
```

## Math reference

See `docs/math_reference.md` for full derivations. Key formulas:

- **Volume**: `V = double Simpson integral of d(x, y) dA`. Validated to
  <1% on smooth shapes, <2% on hemispheres, <5% on cylindrical pits.
- **Surface area**: `SA = integral of sqrt(1 + |grad d|^2) dA`. Validated
  to <3% on cones, <5% on shallow paraboloids, <10% on moderate-aspect
  hemispheroids.
- **GP fusion**: Heteroscedastic Gaussian process with Matérn 5/2 kernel,
  marginal-likelihood-optimized lengthscales, sparse approximation via
  farthest-point inducing-point selection.
- **Uncertainty**: Monte Carlo from the GP posterior (1000 samples by
  default), correlated noise via lengthscale, 95% CIs reported.
- **Graft sizing**: `A_graft = SA + 2*delta*P + 4*delta^2`, recommended =
  mean + 2*std for adequate coverage under uncertainty.
- **Force correction**: `d_true = d_measured - alpha(tissue) * f(force)`,
  table-driven with versioned coefficients.
- **Temporal fusion**: Kalman filter with constant-velocity model in
  per-day units, outliers flagged at >3 sigma Mahalanobis.

## ML models

Three models, all loaded at runtime from S3 with content-hashed weights:

1. **Boundary segmentation** (U-Net): wound vs periwound from RGB photo
2. **Tissue classification** (U-Net++): per-pixel granulation/slough/eschar/etc
3. **Probe tip detection** (YOLOv8 nano): auto-locate probe in photos

Each ships with a `ModelCard` containing training data, validation
metrics, known failure modes; the card is recorded in every measurement's
provenance. See `docs/ml_models.md`.

Heuristic fallbacks are included so the engine runs end-to-end during
development without weights. Production deployments load real weights.

## Provenance

Every measurement carries a `ProvenanceRecord`:
- Engine version, git SHA
- Confidence-weights version, force-correction-table version
- Boundary, tissue, probe model versions and weight content hashes
- SHA-256 of every input artifact
- SHA-256 of intermediate artifacts (fused depth, posterior std)
- Timestamps, processing duration

This is the regulatory audit chain. See `docs/regulatory_traceability.md`.

## Deployment

AWS HIPAA-compliant. See `docs/deployment.md`.

- ECS Fargate (1-10 tasks, autoscaling)
- RDS Postgres with row-level security
- S3 with object lock (6-year retention)
- WAF, GuardDuty, Security Hub
- CloudTrail with log integrity validation

## Validation

See `docs/validation_protocol.md`. The validation harness consists of:
- Synthetic wound test suite (every commit)
- Phantom test suite (every release)
- Clinical correlation (continuous in production)
- Property-based invariants (every commit)
- Regulatory traceability matrix (`docs/regulatory_traceability.md`)
