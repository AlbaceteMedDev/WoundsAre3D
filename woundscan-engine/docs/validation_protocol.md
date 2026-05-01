# Validation Protocol

The engine ships with a multi-tier validation harness. All tiers are
mapped to specific requirements in `regulatory_traceability.md`.

## Tier 1: Synthetic wound test suite (every commit)

Run via `pytest -m regulatory`. Validates the geometry chain on
analytic and quasi-analytic shapes:

| Shape | Volume tol | Surface area tol |
|---|---|---|
| Hemisphere | <2% | not tested (vertical tangent) |
| Cone | <1% | <3% |
| Paraboloid | <1% | <5% |
| Oblate hemispheroid (wide) | <2% | <5% |
| Oblate hemispheroid (moderate) | <2% | <10% |
| Cylindrical pit | <5% | not tested |
| Perlin-irregular paraboloid | <1% (vs numerical truth) | <1% |

## Tier 2: Property-based invariants (every commit)

Hypothesis-based tests for:
- Volume scale equivariance: doubling linear dims multiplies V by 8 (within 2%)
- Surface area scale equivariance: doubling linear dims multiplies SA by 4 (within 2%)
- Translation invariance: rolling the depth+mask preserves V to <1e-4 relative
- Monotonicity: adding depth increases volume
- Confidence interval calibration: 95% CIs contain the truth ≥95%

## Tier 3: Clinical morphology benchmarks

Run via `pytest -m benchmark`. The geometry chain is tested on each
clinical morphology generator (DFU, VLU, pressure injury stages, surgical
dehiscence, traumatic wound). Tolerances <0.5% vs the (high-resolution
numerical) truth carried by each generator.

## Tier 4: Phantom test suite (every release)

Silicone wound phantoms with gold-standard reference measurements:
- Caliper for openings
- Water displacement for volume
- Optical scanning for surface area

12 phantoms covering DFU, VLU, pressure injury stages 2/3/4, surgical
wounds, with varied tissue color, simulated exudate (water spray), and
geometric irregularity. Tested under varied lighting (200-1000 lux) and
incidence angles.

Pass criterion: <2% volume error, <3% surface area error in field
conditions; <1% in ideal conditions.

## Tier 5: Clinical correlation (continuous in production)

Every measurement that has a saline-instillation cross-check feeds the
validation database:
- Each clinician submits saline volumes via the dashboard
- The engine compares saline volume to its own posterior mean
- Bias and dispersion are tracked over time per clinician and aggregate
- Drift alerts fire when error trends exceed the 3% volume threshold

## Tier 6: Regulatory traceability matrix

`docs/regulatory_traceability.md` enumerates every requirement and links
it to the specific test that validates it. Bidirectional coverage is
enforced by build-time check (lint task in CI).

## Running validation locally

```bash
# Fast validation suite (commit gate)
pytest -q -m "regulatory or not benchmark"

# Full benchmarks
pytest -q -m benchmark

# Including integration (requires API deps)
pytest -q tests/integration

# Property invariants
pytest -q tests/regulatory/test_property_invariants.py
```

## Pass/fail policy

- Tier 1-3: failure blocks merge
- Tier 4: failure blocks release
- Tier 5: failure triggers a quality investigation, not an automatic block
- Tier 6: failure blocks merge
