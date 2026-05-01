# Architecture

## Module dependency graph

```
                  ┌──────────┐
                  │   api    │
                  └────┬─────┘
       ┌───────────────┼─────────────────┐
       │               │                 │
   ┌───▼────┐    ┌─────▼─────┐    ┌─────▼─────┐
   │  auth  │    │ pipeline  │    │ monitoring│
   └────────┘    └─────┬─────┘    └───────────┘
                       │
        ┌──────────────┼─────────────┬──────────────┬──────────────┐
        │              │             │              │              │
   ┌────▼────┐    ┌────▼────┐   ┌────▼────┐   ┌─────▼────┐   ┌────▼────┐
   │ capture │    │ quality │   │   ml    │   │  fusion  │   │ geometry│
   └─────────┘    └─────────┘   └─────────┘   └─────┬────┘   └────┬────┘
                                                    │             │
                                              ┌─────▼─────────────▼─────┐
                                              │       validation        │
                                              └─────┬───────────────────┘
                                                    │
                                              ┌─────▼─────┐
                                              │   graft   │
                                              └─────┬─────┘
                                                    │
                                              ┌─────▼─────┐
                                              │  output   │
                                              └─────┬─────┘
                                                    │
                                              ┌─────▼─────┐
                                              │  storage  │
                                              └───────────┘
```

## Data flow

1. **Capture (iOS app)**: Clinician captures multi-modal data (RGB, LiDAR
   depth burst, ARKit poses, fiducials, probe entries, boundary polygon).
2. **Upload**: iOS app obtains presigned S3 URLs (`POST /uploads/presigned`)
   and uploads binaries directly. Returns S3 keys.
3. **Submit**: iOS app sends a `CreateMeasurementRequest` referencing the
   S3 keys (`POST /measurements`).
4. **Pipeline orchestration** (`api/pipeline.py`):
   - Build wound-local grid from boundary polygon
   - Apply force correction to probe measurements
   - Project camera depth into wound-local frame (via ARKit + fiducials)
   - GP fusion → posterior mean + std
   - Geometry: V, SA, perimeter, footprint, max depth, mean depth
   - Monte Carlo uncertainty propagation on V and SA
   - Plausibility checks (geometric, temporal)
   - Quality grade (composite A/B/C/F)
   - Graft sizing per indicated product
   - Build provenance record
5. **Persist**:
   - Result row to Postgres (with provenance JSON)
   - Binary artifacts to S3 with object lock
   - Audit log entry with hash-chain link
6. **Render outputs**:
   - PDF report (with provenance disclosed)
   - FHIR Bundle (downloadable)
   - CSV row (for analytics)
   - Trajectory plot (for the dashboard)

## Configuration & versioning

All version-locked artifacts have an explicit `version` string:
- Confidence weights (`quality.confidence.ConfidenceWeights.version`)
- Force correction table (`fusion.force_correction.ForceCorrectionTable.version`)
- ML model weights (content-hashed SHA-256)

Versions appear in every provenance record. Changing any is a regulatory
deviation that must be re-validated.

## Async processing

The default `POST /measurements` runs synchronously (typical pipeline
takes <2s with 9 anchors and 200x200 grid). For very large captures we
expose the async path via Celery (see `api/worker.py`); the iOS app
polls `GET /measurements/{id}` for completion.

## Error handling

- Pydantic validation at every API boundary
- Typed exceptions throughout the engine; no silent failures
- Sanitized structured logging via structlog (PHI never logged)
- Plausibility failures don't drop the measurement — they're flagged
  in the response and surfaced in the dashboard for clinician review

## Coding standards

- Python 3.11+
- 100% type hints on public APIs
- ruff (all checks) + black + mypy strict
- 80%+ overall coverage, 90%+ on math/ML modules
- All numerical inputs validated for unit, sign, and range
- Reproducibility: every Monte Carlo function accepts a seeded RNG
