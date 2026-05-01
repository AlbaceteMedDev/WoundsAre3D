# Math Reference

This document gives derivations and unit-by-unit formulas for every
numerical quantity the engine produces. Each section maps to a module
in `src/woundscan/`.

Conventions:
- Coordinates: `depth_map[i, j] = d(y_i, x_j)`. Axis 0 is y (row), axis 1 is x (col).
- Depth is positive going INTO the wound. Skin level is `z = 0`.
- Default lengths are cm, default times are seconds, default angles are radians.

## Volume

```
V = ∫∫_R d(x, y) dx dy
```

Discretized via composite Simpson's rule (`scipy.integrate.simpson`).
Fourth-order accurate for smooth integrands. The mask restricts
integration to the wound footprint.

Validated tolerance budget:
- Cone: <1%
- Paraboloid: <1%
- Hemisphere: <2%
- Oblate hemispheroid (wide, shallow): <2%
- Cylindrical pit: <5% (boundary discretization error)

## Surface area (3D wound bed)

```
S_3D = ∫∫_R √(1 + (∂d/∂x)² + (∂d/∂y)²) dA
```

Gradients via central differences (`numpy.gradient`). Surface integral
via Simpson's rule.

The integrand is the Jacobian of the parameterization
`(x, y) → (x, y, d(x, y))`. Limitation: assumes wound bed is a single-
valued function of `(x, y)` — no undermining captured here. Add the
undermining contribution from `geometry.undermining`.

Boundary singularity: as the bed approaches a vertical tangent at the
wound edge, the integrand diverges. The gradient method has tolerance
~10% on near-spherical geometries; bounded-slope wounds are within
~3-5%.

## Perimeter

Two implementations:

1. `compute_perimeter(mask, dx, dy)` — marching-squares contour finding
   from a binary footprint mask. ~8% overshoot due to staircase effect.
2. `compute_perimeter_polygon(vertices_mm)` — sum of segment lengths in
   the clinician-annotated boundary polygon. Subpixel precision.

The polygon path is what production uses. The mask path is a fallback
for ML-only segmentations.

## Undermining

The undermined region at azimuth θ extends radially u(θ) from the wound
edge. We fit a periodic cubic spline to the (clock_position, extent)
measurements and integrate:

```
V_undermining = ∫₀^{2π} ½ u(θ)² h(θ) dθ
S_undermining = ∫₀^{2π} 2 u(θ) h(θ) dθ        (top + bottom of annulus)
```

where h(θ) is the wound bed depth at the edge. Sidewall lateral surface
is added by the sidewall fitting module.

## Heteroscedastic Gaussian process fusion

Given probe points P = {(x_i, y_i, d_i, σ_phys_i)} and camera depth
field with confidence c(x, y), find the posterior over true depth.

Kernel: Matérn 5/2 with separate length scales per dimension:
```
k((x,y),(x',y')) = (1 + √5 r + 5/3 r²) exp(-√5 r)
r² = ((x-x')/ℓₓ)² + ((y-y')/ℓᵧ)²
```

Noise model:
- Probe points: σ_phys (typically 0.5-1.0 mm)
- Camera points: σ_cam(x, y) = σ_base / max(c(x, y), 0.05)

Length scales optimized via marginal likelihood:
```
log p(y | θ) = -½ y^T (K + Σ)^{-1} y - ½ log|K + Σ| - n/2 log(2π)
```

Sparse approximation: for >400 camera anchors, select inducing points
via greedy farthest-point sampling. The exact NumPy backend handles up
to ~600 total anchors at 200×200 grids; for larger problems the
GPyTorch backend (when available) provides O(m³) variational inference.

Output: posterior mean d_fused(x, y), posterior pointwise std σ_fused,
correlation length scale (geometric mean of ℓₓ, ℓᵧ).

## Multi-view bundle adjustment

Given N views with initial ARKit poses T_i^{init}, fiducial markers at
known positions p_world, and observed pixels p_pix^i, find pose
corrections that minimize:

```
L = Σᵢ Σⱼ ||π(T_i^{-1} p_world^j; K_i) - p_pix^{i,j}||²
```

where π is the standard pinhole projection. Optimizer: Levenberg-
Marquardt per-view, parameterized by 6-DoF Rodrigues rotation + translation.

## Bayesian temporal fusion (Kalman)

State: x = (V, S, h_max, dV/dt, dS/dt, dh/dt). Time step is in DAYS.

Process model (constant velocity):
```
x_t = F x_{t-1} + w
F = [[I_3 | dt I_3], [0 | I_3]]
Q = G diag(q_V, q_S, q_h) G^T,  G = [½dt²; dt]
```

Default q values are per-day variance rates of change rate:
- q_V = 0.01 (cm³/day)²
- q_S = 0.05 (cm²/day)²
- q_h = 0.005 (cm/day)²

Observation model: `z = H x + v`, `H = [I_3 | 0]`, `R` from GP posterior.

Outliers: flagged when Mahalanobis distance > 3σ.

## Force correction

Empirical correction:
```
d_true = d_measured - α(tissue_type) · f(force_category)
```

Where:
- α depends on tissue type (granulation: 0.3-1.2 mm; fibrous: 0.2-0.8 mm; eschar: 0.1-0.4 mm)
- f maps clinician force category {light, medium, firm} to magnitude

Per-measurement uncertainty inflated:
```
σ_corrected² = σ_original² + (½ · α · f)²
```

## Volume / surface area uncertainty (Monte Carlo)

For each MC sample:
1. Sample depth field from posterior:
   - Independent (depth_std only): pointwise Gaussian
   - Correlated (+ correlation_length): Gaussian-smoothed white noise, rescaled
   - Full covariance: multivariate Gaussian
2. Compute V or SA on the sampled depth
3. Aggregate samples → mean, std, 95% CI

Default: 1000 samples. We always emit a warning when computing SA
uncertainty without a correlation length, because pointwise-independent
noise inflates the gradient-based SA integrand.

## Graft sizing

```
A_graft = S_3D + 2δ·P + 4δ²
A_recommended = mean(A_graft) + 2·std(A_graft)
```

The 2-sigma upper bound ensures adequate coverage under measurement
uncertainty. The chosen stock size is the smallest available that
exceeds A_recommended. Both the point estimate and recommendation are
disclosed in the report; clinician picks.

## Composite confidence map

```
c(x,y) = 0.25·(1 - specularity)
       + 0.20·texture_contrast
       + 0.15·lighting_uniformity
       + 0.15·(1 - motion_artifact)
       + 0.10·edge_distance
       + 0.10·frame_consistency
       + 0.05·boundary_confidence
```

Each component is in [0, 1]. Weights are version-locked
(`ConfidenceWeights.version`); changing them is a regulatory deviation.

## Quality grade

Composite score in [0, 1]:
- 0.25 · mean_confidence
- 0.20 · anchor_count_quality (5 anchors = 0.5, 9+ = 1.0)
- 0.15 · camera_probe_agreement (z<=1 → 1, z>=4 → 0)
- 0.15 · fiducial_quality (count + reprojection error)
- 0.10 · frame_consistency
- 0.10 · ml_segmentation_confidence
- 0.05 · photo_focus_score

Grade thresholds: A ≥ 0.85, B ≥ 0.70, C ≥ 0.50, otherwise F.
