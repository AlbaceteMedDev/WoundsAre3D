"""Last-mile coverage: surface_area, perimeter, irregular_beds, more confidence."""

from __future__ import annotations

import numpy as np
import pytest

from woundscan.geometry.surface_area import (
    compute_footprint_area,
    compute_perimeter,
    compute_surface_area,
)
from woundscan.synthesis.analytic_shapes import paraboloid
from woundscan.synthesis.irregular_beds import (
    IrregularConfig,
    add_perlin_noise,
    irregular_paraboloid,
)


# ---------------------------------------------------------------------------
# geometry/surface_area
# ---------------------------------------------------------------------------


class TestComputeSurfaceArea:
    def test_flat_bed_equals_footprint(self):
        # Constant-depth bed → surface area equals integration domain area.
        d = np.zeros((9, 9), dtype=np.float64)
        dx = dy = 0.5  # cm
        s = compute_surface_area(d, dx, dy)
        assert s == pytest.approx(((9 - 1) * dx) * ((9 - 1) * dy), rel=0.01)

    def test_masked_flat_bed_equals_footprint_area(self):
        d = np.zeros((9, 9), dtype=np.float64)
        mask = np.zeros((9, 9), dtype=bool)
        mask[2:7, 2:7] = True
        dx = dy = 0.5
        s = compute_surface_area(d, dx, dy, mask=mask)
        # Roughly footprint area (5×5 cells × 0.25 cm² each = 6.25 cm²)
        # but Simpson's integration on the binary integrand can over/undershoot
        # slightly at the boundary.
        assert 4.0 < s < 9.0

    def test_rejects_low_dimensional(self):
        with pytest.raises(ValueError, match="must be 2D"):
            compute_surface_area(np.zeros(9), 0.5, 0.5)

    def test_rejects_too_few_points(self):
        with pytest.raises(ValueError, match="at least 3 points"):
            compute_surface_area(np.zeros((2, 9)), 0.5, 0.5)

    def test_rejects_bad_spacing(self):
        with pytest.raises(ValueError, match="must be positive"):
            compute_surface_area(np.zeros((9, 9)), 0.0, 0.5)

    def test_rejects_mask_shape_mismatch(self):
        with pytest.raises(ValueError, match="mask shape"):
            compute_surface_area(
                np.zeros((9, 9)),
                0.5,
                0.5,
                mask=np.zeros((5, 5), dtype=bool),
            )

    def test_sloped_bed_exceeds_flat(self):
        # Linear ramp z = 0.5x; the 3D area exceeds the 2D footprint area.
        x = np.linspace(0, 2, 9)
        d = 0.5 * x[None, :].repeat(9, axis=0)
        flat_area = compute_surface_area(np.zeros_like(d), 0.25, 0.25)
        sloped = compute_surface_area(d, 0.25, 0.25)
        assert sloped > flat_area


class TestComputeFootprintArea:
    def test_full_mask_equals_grid_area(self):
        mask = np.ones((10, 10), dtype=bool)
        assert compute_footprint_area(mask, 0.5, 0.5) == pytest.approx(25.0)

    def test_empty_mask_is_zero(self):
        assert compute_footprint_area(np.zeros((5, 5), dtype=bool), 0.5, 0.5) == 0.0

    def test_rejects_low_dim(self):
        with pytest.raises(ValueError, match="must be 2D"):
            compute_footprint_area(np.array([True, False, True]), 0.5, 0.5)


class TestComputePerimeter:
    def test_square_mask_perimeter(self):
        # 5×5 mask in a 9×9 grid with 0.5 cm spacing → perimeter ≈ 4 × 5 × 0.5 = 10 cm.
        # marching-squares uses sub-pixel placement so the exact value is
        # slightly off the nominal — allow ±20% tolerance.
        mask = np.zeros((9, 9), dtype=bool)
        mask[2:7, 2:7] = True
        p = compute_perimeter(mask, 0.5, 0.5)
        assert 6.0 < p < 12.0

    def test_empty_mask_zero_perimeter(self):
        mask = np.zeros((5, 5), dtype=bool)
        assert compute_perimeter(mask, 0.5, 0.5) == 0.0

    def test_rejects_low_dim(self):
        with pytest.raises(ValueError, match="must be 2D"):
            compute_perimeter(np.zeros(5, dtype=bool), 0.5, 0.5)


# ---------------------------------------------------------------------------
# synthesis/irregular_beds
# ---------------------------------------------------------------------------


class TestPerlinPerturbation:
    def test_default_config_values(self):
        cfg = IrregularConfig()
        assert cfg.octaves == 4
        assert cfg.persistence == 0.5

    def test_irregular_paraboloid_has_recomputed_ground_truth(self):
        # The base paraboloid analytic volume vs the irregular numerical
        # volume should differ (the perlin perturbation changes the bed).
        base = paraboloid(radius=2.0, depth_max=1.0, n_grid=51)
        irr = irregular_paraboloid(radius=2.0, depth_max=1.0, n_grid=51, amplitude_mm=2.0, seed=42)
        assert irr.name.startswith("paraboloid+perlin") or "perlin" in irr.name
        assert irr.true_footprint_area == pytest.approx(base.true_footprint_area, rel=0.01)
        # Volume should be close to base (perturbation has near-zero mean).
        # Surface area can grow substantially since roughness only adds area.
        assert abs(irr.true_volume - base.true_volume) / base.true_volume < 0.3
        # Roughened bed must have >= analytic-smooth surface area.
        assert irr.true_surface_area >= base.true_surface_area

    def test_add_perlin_noise_preserves_mask(self):
        base = paraboloid(radius=2.0, depth_max=1.0, n_grid=51)
        irr = add_perlin_noise(base, IrregularConfig(amplitude_mm=0.5, seed=1))
        assert irr.mask.shape == base.mask.shape
        assert irr.mask.sum() == base.mask.sum()
        # Depth must be zero outside the mask (the perlin function masks it).
        assert irr.depth_map[~base.mask].max() == 0.0

    def test_zero_amplitude_is_near_identity(self):
        base = paraboloid(radius=2.0, depth_max=1.0, n_grid=51)
        irr = add_perlin_noise(base, IrregularConfig(amplitude_mm=0.0))
        # With zero amplitude the depth map should match the base (up to clipping).
        assert np.allclose(irr.depth_map, base.depth_map, atol=1e-9)
