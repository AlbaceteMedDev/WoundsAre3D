"""Tests for synthesis: irregular beds, clinical morphologies, degradation."""

import numpy as np
import pytest

from woundscan.geometry.surface_area import compute_surface_area
from woundscan.geometry.volume import compute_volume
from woundscan.synthesis.analytic_shapes import paraboloid
from woundscan.synthesis.clinical_morphologies import (
    diabetic_foot_ulcer,
    pressure_injury_stage_3,
    surgical_dehiscence,
    venous_leg_ulcer,
)
from woundscan.synthesis.degradation import (
    DegradationConfig,
    add_sensor_noise,
    add_specular_highlights,
    degrade_synthetic_wound,
)
from woundscan.synthesis.ground_truth import (
    GroundTruth,
    compute_ground_truth,
    relative_error,
)
from woundscan.synthesis.irregular_beds import (
    IrregularConfig,
    add_perlin_noise,
    irregular_paraboloid,
)


class TestIrregularBeds:
    def test_irregular_preserves_footprint(self):
        base = paraboloid(radius=2.0, depth_max=1.0, n_grid=151)
        irreg = add_perlin_noise(base, IrregularConfig(amplitude_mm=0.5, seed=42))
        assert (irreg.mask == base.mask).all()

    def test_irregular_volume_close_to_base(self):
        base = paraboloid(radius=2.0, depth_max=1.0, n_grid=151)
        irreg = add_perlin_noise(base, IrregularConfig(amplitude_mm=0.5, seed=42))
        assert abs(irreg.true_volume - base.true_volume) / base.true_volume < 0.10

    def test_irregular_paraboloid_helper(self):
        w = irregular_paraboloid(radius=2.0, depth_max=1.0, n_grid=151, amplitude_mm=0.5)
        V = compute_volume(w.depth_map, w.dx, w.dy, mask=w.mask)
        assert abs(V - w.true_volume) / w.true_volume < 0.01


class TestClinicalMorphologies:
    @pytest.mark.parametrize("fn", [diabetic_foot_ulcer, venous_leg_ulcer, pressure_injury_stage_3])
    def test_all_produce_valid_wounds(self, fn):
        w = fn(seed=0)
        assert w.mask.any()
        assert w.true_volume > 0
        assert w.true_surface_area > 0
        assert w.true_footprint_area > 0

    def test_surgical_dehiscence_is_elongated(self):
        w = surgical_dehiscence(length_cm=8.0, width_cm=1.0, depth_cm=2.0, seed=0)
        # Elongated wounds have larger linear extent than width
        ny, nx = w.mask.shape
        rows_filled = np.any(w.mask, axis=1).sum()
        cols_filled = np.any(w.mask, axis=0).sum()
        assert max(rows_filled, cols_filled) >= 2 * min(rows_filled, cols_filled)


class TestDegradation:
    def test_sensor_noise_changes_depth(self):
        from woundscan.synthesis.analytic_shapes import cone

        w = cone(radius=2.0, depth_max=1.0, n_grid=51)
        rng = np.random.default_rng(0)
        degraded = add_sensor_noise(w.depth_map, distance_m=0.3, noise_mm_per_meter=3.0, rng=rng)
        # The means should differ but be close
        assert not np.array_equal(w.depth_map, degraded)
        diff_std = float(np.std(degraded - w.depth_map))
        assert 0.0 < diff_std < 0.5

    def test_specular_drops_pixels(self):
        from woundscan.synthesis.analytic_shapes import cone

        w = cone(radius=2.0, depth_max=1.0, n_grid=51)
        out, mask = add_specular_highlights(
            w.depth_map, fraction=0.05, rng=np.random.default_rng(0)
        )
        n_dropped = int(mask.sum())
        assert n_dropped > 0
        assert np.isnan(out).sum() == n_dropped

    def test_full_pipeline_runs(self):
        from woundscan.synthesis.analytic_shapes import paraboloid

        w = paraboloid(radius=2.0, depth_max=1.0, n_grid=51)
        rgb = (np.random.default_rng(0).random((51, 51, 3)) * 255).astype(np.uint8)
        cfg = DegradationConfig(
            depth_noise_mm_per_meter=3.0,
            motion_blur_pixels=0.5,
            specular_fraction=0.02,
            lighting_gradient=0.2,
            seed=0,
        )
        depth, rgb_out, drop = degrade_synthetic_wound(w, rgb, cfg)
        assert depth.shape == w.depth_map.shape
        assert rgb_out is not None and rgb_out.shape == rgb.shape


class TestGroundTruth:
    def test_relative_error(self):
        assert relative_error(1.05, 1.0) == pytest.approx(0.05)
        assert relative_error(0.0, 0.0) == 0.0
        assert relative_error(1.0, 0.0) == float("inf")

    def test_compute_ground_truth_wraps(self):
        from woundscan.synthesis.analytic_shapes import cone

        w = cone(radius=2.0, depth_max=1.0)
        gt = compute_ground_truth(w)
        assert isinstance(gt, GroundTruth)
        assert gt.volume_cm3 == pytest.approx(w.true_volume)
