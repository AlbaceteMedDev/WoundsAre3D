# WoundScan Geometry Module

Validated geometry foundation for the WoundScan platform.

This package implements 3D wound bed surface area, volume, perimeter, and
graft sizing math, with full Monte Carlo uncertainty quantification. Every
formula is validated against analytic ground truth on synthetic wounds
covering the clinical morphology range.

This is the foundation module for the larger WoundScan platform. Drop it
into your project as `src/woundscan/geometry/` and `src/woundscan/synthesis/`
and build the rest of the system on top of it.

## Why this exists

Every accuracy claim in WoundScan downstream of this module depends on the
math here being correct. The validation suite ensures it stays correct
through future changes. If any test in `tests/test_geometry.py` regresses,
the entire system's accuracy claims are invalidated.

This module is intentionally small and self-contained. It has only three
runtime dependencies (numpy, scipy, scikit-image) and no internal coupling
to the rest of the WoundScan codebase, so it can be imported, tested, and
audited independently.

## Installation

```bash
pip install -e ".[dev]"
```

## Validate the math

```bash
pytest tests/ -v
```

You should see 33 tests pass. If any fail, do not use this package — the
math has regressed.

## Demo

```bash
python examples/demo.py
```

Shows volume, surface area, and graft sizing on four representative
wounds (shallow DFU, moderate VLU, stage 4 pressure injury, surgical
wound) with full uncertainty quantification.

## Public API

### Volume

```python
from woundscan.geometry.volume import (
    compute_volume,            # primary
    compute_volume_trapezoid,  # fallback for noisy data
    compute_mean_depth,        # area-weighted mean
)
```

### Surface area

```python
from woundscan.geometry.surface_area import (
    compute_surface_area,    # 3D bed surface via gradient integral
    compute_footprint_area,  # 2D opening area at skin level
    compute_perimeter,       # wound edge length at skin level
)
```

### Uncertainty quantification

```python
from woundscan.geometry.uncertainty import (
    compute_volume_with_uncertainty,
    compute_surface_area_with_uncertainty,
    UncertaintyResult,  # dataclass: mean, std, ci_95_low, ci_95_high, median
)
```

### Synthetic wounds (for testing and validation)

```python
from woundscan.synthesis.analytic_shapes import (
    hemisphere,      # bowl with spherical bed
    cone,            # linear-slope inverted cone
    paraboloid,      # smooth parabolic bowl
    hemispheroid,    # general half-ellipsoid (oblate, prolate, sphere)
    flat_disk,       # cylindrical pit (volume validation only)
    AnalyticWound,   # dataclass returned by all generators
)
```

## Math reference

### Volume

```
V = integral over R of d(x, y) dx dy
```

Discretized with composite Simpson's rule via `scipy.integrate.simpson`.
Fourth-order accurate for smooth depth fields.

### Surface area

```
S = integral over R of sqrt(1 + (dd/dx)^2 + (dd/dy)^2) dA
```

The integrand is the Jacobian of the parameterization (x, y) -> (x, y, d(x, y)).
Gradients via central differences (numpy.gradient). Surface integral via
Simpson's rule.

Limitation: assumes wound bed is a single-valued function of (x, y) - one
depth per skin-level point. Does NOT capture undermining, tunneling, or
vertical sidewalls. Add those as supplemental measurements downstream.

### Graft size

```
A_graft = S_3D + 2 * delta * P + 4 * delta^2
```

where delta is the IFU-mandated overlap. Implemented in
`compute_surface_area` + `compute_perimeter` + a one-line application of
the formula.

### Uncertainty

Monte Carlo sampling from a depth-field posterior. Three input modes:

1. Pointwise std (independent noise) — use for volume, NOT for surface area
2. Pointwise std + correlation_length_cm — recommended for both
3. Full covariance matrix — exact for GP posteriors

For surface area, you MUST use option 2 or 3. Option 1 amplifies
high-frequency noise through the gradient operator and inflates
uncertainty. The function emits a warning if option 1 is used.

## Validation tolerances

These are the accuracy budgets enforced by the test suite. Numbers are
relative error vs. analytic ground truth.

| Shape | Volume | Surface area |
|---|---|---|
| Cone | <1% | <3% |
| Paraboloid | <1% | <5% |
| Hemisphere | <2% | not tested (vertical tangent at boundary) |
| Oblate hemispheroid (wide, shallow) | <2% | <5% |
| Oblate hemispheroid (moderate) | <2% | <10% |
| Prolate hemispheroid | <3% | not tested (vertical tangent) |
| Flat disk (cylindrical) | <5% | not applicable |

These tolerances are appropriate for clinical use. Sub-1% accuracy is
achievable on smooth shapes (cone, paraboloid, mild hemispheroid) — the
typical wound morphology. Steeper geometries hit the boundary singularity
limitation of the gradient method, where the surface area integrand
diverges; this is mathematically unavoidable for the gradient-integral
approach. Real wound beds with sloped walls fall well within the tested
regime.

## Integration with the larger WoundScan platform

This module is module #3 in the build order from the project brief:

1. Project scaffolding
2. Synthetic wound generators (`synthesis/`) — included here
3. Geometry math (`geometry/`) — included here
4. Confidence map computation
5. Depth field fusion (weighted blend, then Gaussian process)
6. ML models (boundary, tissue, probe detection)
7. API, storage, auth
8. iOS app
9. Web dashboard

When you build modules 4-9, import from `woundscan.geometry.*` for all
volume, surface area, perimeter, and uncertainty computations. Do not
reimplement.

## What this module does NOT include (and where to find it)

- **Sensor fusion** (camera + probe combination) — module 5
- **ML models** — module 6
- **Confidence map computation** — module 4
- **Boundary segmentation** — module 6
- **Force correction for probe compression** — module 5
- **Cross-visit Bayesian temporal fusion** — module 5
- **Multi-view bundle adjustment** — module 5

Each of those modules consumes the outputs of this module (and provides
inputs to it). Build them in order.

## Coding standards

- numpy/scipy idiomatic
- All public functions have full numpy-style docstrings with units
- All numerical inputs validated for unit, sign, and range
- Type hints on all public signatures
- No silent failures — typed exceptions with diagnostic messages
- Test coverage on math functions: 100%

## Reproducibility

All Monte Carlo functions accept an `rng: np.random.Generator` parameter.
When omitted, a default seeded RNG (`np.random.default_rng(seed=0)`) is
used. Same inputs + same RNG = exact same outputs. This is required for
regulatory traceability and audit defense.

## What changes when you commercialize

For internal use under the clinical decision support carve-out, this
module is sufficient as-is. For an FDA 510(k) submission, you'll need:

- Documented design controls (this code is the artifact)
- Verification protocol (this test suite is the protocol)
- Validation against physical phantoms (separate work)
- Risk analysis (separate document)
- Software bill of materials

The code itself does not need to change. Build the rest of the platform
to the same bar this module sets.
