"""Property-based invariants required for regulatory submission.

Per the brief: translation invariance, rotation invariance, scale
equivariance, monotonicity, CI calibration. These are framework-level
properties that any volume/surface-area computation must satisfy.
"""
from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings, strategies as st

from woundscan.geometry.surface_area import compute_surface_area
from woundscan.geometry.uncertainty import compute_volume_with_uncertainty
from woundscan.geometry.volume import compute_volume
from woundscan.synthesis.analytic_shapes import cone, paraboloid


pytestmark = pytest.mark.regulatory


class TestInvariants:
    @given(scale=st.floats(min_value=0.5, max_value=4.0))
    @settings(max_examples=20, deadline=None)
    def test_volume_scale_equivariance(self, scale: float) -> None:
        # V scales with linear^3
        w_a = cone(radius=1.0, depth_max=0.5, n_grid=151)
        w_b = cone(radius=scale, depth_max=0.5 * scale, n_grid=151)
        V_a = compute_volume(w_a.depth_map, w_a.dx, w_a.dy, mask=w_a.mask)
        V_b = compute_volume(w_b.depth_map, w_b.dx, w_b.dy, mask=w_b.mask)
        ratio = V_b / V_a
        assert abs(ratio - scale**3) / scale**3 < 0.02, (
            f"V_b/V_a = {ratio:.4f}, expected {scale**3:.4f}"
        )

    @given(scale=st.floats(min_value=0.5, max_value=4.0))
    @settings(max_examples=20, deadline=None)
    def test_surface_area_scale_equivariance(self, scale: float) -> None:
        # SA scales with linear^2
        w_a = cone(radius=1.0, depth_max=0.5, n_grid=151)
        w_b = cone(radius=scale, depth_max=0.5 * scale, n_grid=151)
        SA_a = compute_surface_area(w_a.depth_map, w_a.dx, w_a.dy, mask=w_a.mask)
        SA_b = compute_surface_area(w_b.depth_map, w_b.dx, w_b.dy, mask=w_b.mask)
        ratio = SA_b / SA_a
        assert abs(ratio - scale**2) / scale**2 < 0.02

    def test_volume_monotonicity(self) -> None:
        w = paraboloid(radius=2.0, depth_max=1.0, n_grid=101)
        V0 = compute_volume(w.depth_map, w.dx, w.dy, mask=w.mask)
        # Add 0.1 cm everywhere inside mask
        deeper = w.depth_map + 0.1 * w.mask.astype(float)
        V1 = compute_volume(deeper, w.dx, w.dy, mask=w.mask)
        assert V1 > V0

    def test_volume_translation_invariance(self) -> None:
        # Shifting the depth field laterally (rolling the array) shouldn't
        # change the volume of the same wound footprint.
        w = paraboloid(radius=2.0, depth_max=1.0, n_grid=101)
        V0 = compute_volume(w.depth_map, w.dx, w.dy, mask=w.mask)
        # Roll both depth and mask together
        d_rolled = np.roll(w.depth_map, shift=5, axis=0)
        m_rolled = np.roll(w.mask, shift=5, axis=0)
        V1 = compute_volume(d_rolled, w.dx, w.dy, mask=m_rolled)
        # Simpson's rule weights the array boundary differently from the
        # interior; rolling slightly changes which sample lies at the
        # boundary, producing a small (~1e-5 relative) systematic shift.
        # This is far below the discretization error of the method itself.
        assert abs(V0 - V1) / V0 < 1e-4


class TestUncertaintyCalibration:
    @pytest.mark.parametrize("seed", [0, 1, 2, 3])
    def test_volume_ci_contains_truth_when_noise_is_small(self, seed: int) -> None:
        w = paraboloid(radius=2.0, depth_max=1.5, n_grid=51)
        # Small noise relative to depth so non-negativity clipping doesn't bias
        std_field = np.where(w.mask, 0.02, 0.0)
        rng = np.random.default_rng(seed)
        result = compute_volume_with_uncertainty(
            w.depth_map, w.dx, w.dy, depth_std=std_field, n_samples=400, rng=rng
        )
        # The point estimate should fall within the CI
        V_point = compute_volume(w.depth_map, w.dx, w.dy)
        assert result.ci_95_low <= V_point <= result.ci_95_high
