"""Tests for fusion/bundle_adjustment.

The optimizer tests run in a subprocess: scipy.optimize.least_squares
silently fails under coverage's CTracer + numpy 1.26 reload race on
Py3.12 (same root cause as the matplotlib race in trajectory_plot tests).
The non-LM paths (shape validation, all-views-skipped, raw projection)
stay in-process so they contribute to the coverage gauge.
"""

from __future__ import annotations

import json
import subprocess
import sys

import numpy as np
import pytest

from woundscan.fusion.bundle_adjustment import (
    BundleAdjustmentResult,
    _project_3d_to_pixel,
    run_bundle_adjustment,
)


def _intrinsics() -> np.ndarray:
    return np.array(
        [[500.0, 0.0, 320.0], [0.0, 500.0, 240.0], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )


# ---------------------------------------------------------------------------
# In-process: non-LM paths only.
# ---------------------------------------------------------------------------


class TestRunBundleAdjustmentNonLM:
    def test_rejects_wrong_pose_shape(self):
        bad = np.eye(4)  # (4,4) instead of (n,4,4)
        with pytest.raises(ValueError):
            run_bundle_adjustment(
                initial_poses=bad,
                intrinsics=[_intrinsics()],
                fiducial_points_world=np.zeros((4, 3)),
                fiducial_points_pixels=[np.zeros((4, 2))],
            )

    def test_returns_inf_residual_when_all_views_skipped(self):
        # 4 fiducials in world but only 3 pixels per view → every view is
        # skipped by the loop's `pts2d.shape[0] != world.shape[0]` guard.
        # Result: every correction is zero, residual list is empty → inf.
        initial = np.stack([np.eye(4), np.eye(4)])
        result = run_bundle_adjustment(
            initial_poses=initial,
            intrinsics=[_intrinsics()] * 2,
            fiducial_points_world=np.zeros((4, 3)),
            fiducial_points_pixels=[np.zeros((3, 2)), np.zeros((3, 2))],
        )
        assert isinstance(result, BundleAdjustmentResult)
        assert result.final_residual_pix == float("inf")
        assert result.converged is False
        assert np.all(result.pose_correction_mm == 0.0)


class TestProject3dToPixel:
    def test_optical_center_projects_to_principal_point(self):
        K = _intrinsics()
        pts = np.array([[0.0, 0.0, 0.30]])
        pix = _project_3d_to_pixel(pts, np.eye(4), K)
        assert pix[0, 0] == pytest.approx(320.0, abs=0.01)
        assert pix[0, 1] == pytest.approx(240.0, abs=0.01)

    def test_lateral_offset_projects_correctly(self):
        K = _intrinsics()
        pts = np.array([[0.05, 0.0, 0.30]])
        pix = _project_3d_to_pixel(pts, np.eye(4), K)
        assert pix[0, 0] == pytest.approx(320.0 + 500.0 * 0.05 / 0.30, abs=0.01)


# ---------------------------------------------------------------------------
# Subprocess-isolated: LM optimizer paths.
# ---------------------------------------------------------------------------


_SUBPROCESS_RUNNER = r"""
import json
import sys
import numpy as np
from scipy.spatial.transform import Rotation as R
from woundscan.fusion.bundle_adjustment import _project_3d_to_pixel, run_bundle_adjustment

def cam2world(pos, look):
    z = look - pos
    z = z / np.linalg.norm(z)
    up = np.array([0.0, 1.0, 0.0])
    x = np.cross(up, z)
    x = x / np.linalg.norm(x)
    y = np.cross(z, x)
    p = np.eye(4)
    p[:3, 0] = x; p[:3, 1] = y; p[:3, 2] = z; p[:3, 3] = pos
    return p

def perturb(p, rng):
    axis = rng.normal(size=3); axis = axis / np.linalg.norm(axis)
    drot = R.from_rotvec(axis * np.radians(1.0)).as_matrix()
    dt = rng.normal(scale=0.005, size=3)
    q = p.copy(); q[:3, :3] = drot @ p[:3, :3]; q[:3, 3] = p[:3, 3] + dt
    return q

rng = np.random.default_rng(42)
K = np.array([[500., 0, 320], [0, 500, 240], [0, 0, 1.0]])
# Non-coplanar fiducials so the PnP problem has a unique solution.
fiducials = np.array(
    [[-0.025, 0.025, 0.000],
     [ 0.025, 0.025, 0.005],
     [ 0.025,-0.025, 0.000],
     [-0.025,-0.025, 0.010]]
)
gt_poses = np.stack([
    cam2world(np.array([ 0.00, 0.05, 0.30]), np.zeros(3)),
    cam2world(np.array([-0.10, 0.05, 0.28]), np.zeros(3)),
    cam2world(np.array([ 0.10, 0.05, 0.28]), np.zeros(3)),
])
pixels = [_project_3d_to_pixel(fiducials, np.linalg.inv(gt_poses[i]), K) for i in range(3)]

# Drop_view arg: -1 = no drop, k = drop last pixel of view k.
drop_view = int(sys.argv[1])
mod_pixels = [p.tolist() for p in pixels]
if drop_view >= 0:
    mod_pixels[drop_view] = mod_pixels[drop_view][:-1]

perturbed = np.stack([perturb(gt_poses[i], rng) for i in range(3)])
result = run_bundle_adjustment(
    initial_poses=perturbed,
    intrinsics=[K] * 3,
    fiducial_points_world=fiducials,
    fiducial_points_pixels=[np.array(p) for p in mod_pixels],
    max_iterations=200,
    tolerance_pix=0.5,
)
out = {
    "converged": bool(result.converged),
    "final_residual_pix": float(result.final_residual_pix),
    "pose_correction_mm": result.pose_correction_mm.tolist(),
    "pose_rotation_correction_deg": result.pose_rotation_correction_deg.tolist(),
    "refined_positions": [result.refined_poses[i][:3, 3].tolist() for i in range(3)],
    "gt_positions": [gt_poses[i][:3, 3].tolist() for i in range(3)],
}
sys.stdout.write(json.dumps(out))
"""


def _run_ba_subprocess(drop_view: int = -1) -> dict:
    proc = subprocess.run(
        [sys.executable, "-c", _SUBPROCESS_RUNNER, str(drop_view)],
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr.decode(errors='replace')}"
    return json.loads(proc.stdout)


class TestRunBundleAdjustmentLM:
    """LM optimizer paths — run in a clean child interpreter."""

    @pytest.fixture(scope="class")
    def result(self) -> dict:
        return _run_ba_subprocess()

    def test_reduces_reprojection_error_below_tolerance(self, result):
        assert result["converged"] is True
        assert result["final_residual_pix"] < 0.5

    def test_pose_corrections_match_injected_noise(self, result):
        # Perturbation was ~5mm + 1° per view → corrections should be in that
        # neighborhood (not zero, not huge).
        for v, mm in enumerate(result["pose_correction_mm"]):
            assert 1.0 < mm < 50.0, f"view {v}: {mm}mm out of plausible range"
        for v, deg in enumerate(result["pose_rotation_correction_deg"]):
            assert 0.1 < deg < 5.0, f"view {v}: {deg}° out of plausible range"

    def test_refined_positions_close_to_ground_truth(self, result):
        for v in range(3):
            err_mm = float(
                np.linalg.norm(
                    np.array(result["refined_positions"][v])
                    - np.array(result["gt_positions"][v])
                )
                * 1000.0
            )
            assert err_mm < 1.0, f"view {v}: {err_mm:.3f}mm > 1mm"

    def test_skips_view_with_mismatched_pixel_count(self):
        result = _run_ba_subprocess(drop_view=1)
        # View 1 was skipped (mismatched pixel count) → its correction is 0.
        # Views 0 and 2 still optimize normally.
        assert result["pose_correction_mm"][1] == 0.0
        assert result["pose_correction_mm"][0] > 0.0
        assert result["pose_correction_mm"][2] > 0.0
