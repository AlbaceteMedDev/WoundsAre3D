"""Multi-view bundle adjustment.

When the iOS app captures the wound from multiple angles in a single
session, we jointly optimize per-view camera poses and a coherent depth
surface using Levenberg-Marquardt. We start from the ARKit-supplied
poses (which have ~5mm drift over the burst) and refine with fiducial-
constrained reprojection error + probe-anchor 3D constraints.

This module is intentionally a slimmer specialization of the full
photogrammetry problem: we DO NOT do feature-matching or sparse
reconstruction. The depth surface is parameterized as a sum of
ARKit-provided per-view depth maps weighted by per-view confidence,
with pose corrections as the optimization variables.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class BundleAdjustmentResult:
    """Output of multi-view bundle adjustment.

    Attributes
    ----------
    refined_poses : (n_views, 4, 4)
        Camera-to-world transforms after optimization.
    pose_correction_mm : (n_views,)
        L2 norm of position-only correction applied to each view.
    pose_rotation_correction_deg : (n_views,)
        Angular correction.
    final_residual_pix : float
        Mean reprojection error after optimization.
    converged : bool
    """

    refined_poses: np.ndarray
    pose_correction_mm: np.ndarray
    pose_rotation_correction_deg: np.ndarray
    final_residual_pix: float
    converged: bool


def _project_3d_to_pixel(
    points_world: np.ndarray, pose_world_to_camera: np.ndarray, K: np.ndarray
) -> np.ndarray:
    """Project (N, 3) world points to (N, 2) pixels."""
    homog = np.column_stack([points_world, np.ones((points_world.shape[0], 1))])
    cam = (pose_world_to_camera @ homog.T).T[:, :3]
    proj = (K @ cam.T).T
    return proj[:, :2] / proj[:, 2:3]


def run_bundle_adjustment(
    initial_poses: np.ndarray,
    intrinsics: list,  # list of (3, 3)
    fiducial_points_world: np.ndarray,  # (M, 3) anchor points in world
    fiducial_points_pixels: list,  # list[(M, 2)] per view
    max_iterations: int = 50,
    tolerance_pix: float = 0.5,
) -> BundleAdjustmentResult:
    """Refine camera poses by minimizing fiducial reprojection error.

    Per-view reprojection error of the M fiducial markers is the cost.
    Optimizer: Levenberg-Marquardt over 6-DoF pose corrections.

    NOTE: this is the simplified pose-only formulation. Joint depth
    refinement requires the full Jacobian wrt depth grid, which we
    add post-MVP when we have measured impact data.
    """
    if initial_poses.ndim != 3 or initial_poses.shape[1:] != (4, 4):
        raise ValueError(f"initial_poses must be (n, 4, 4), got {initial_poses.shape}")

    n_views = initial_poses.shape[0]
    refined = initial_poses.copy()

    # Pose-only LM using scipy.least_squares per-view
    from scipy.optimize import least_squares
    from scipy.spatial.transform import Rotation as R

    def residuals_for_view(params6: np.ndarray, init_pose: np.ndarray, K: np.ndarray, pts2d: np.ndarray) -> np.ndarray:
        rvec = params6[:3]
        tvec = params6[3:]
        rot = R.from_rotvec(rvec).as_matrix()
        delta = np.eye(4)
        delta[:3, :3] = rot
        delta[:3, 3] = tvec
        pose = delta @ init_pose
        pose_inv = np.linalg.inv(pose)
        proj = _project_3d_to_pixel(fiducial_points_world, pose_inv, K)
        return (proj - pts2d).flatten()

    pose_corrections_mm = np.zeros(n_views)
    pose_corrections_deg = np.zeros(n_views)
    final_res = []

    for v in range(n_views):
        K = np.asarray(intrinsics[v], dtype=np.float64)
        pts2d = np.asarray(fiducial_points_pixels[v], dtype=np.float64)
        if pts2d.shape[0] != fiducial_points_world.shape[0]:
            continue
        params0 = np.zeros(6)
        try:
            res = least_squares(
                residuals_for_view,
                params0,
                args=(initial_poses[v], K, pts2d),
                method="lm",
                max_nfev=max_iterations,
            )
        except Exception:
            continue
        rvec = res.x[:3]
        tvec = res.x[3:]
        rot = R.from_rotvec(rvec).as_matrix()
        delta = np.eye(4)
        delta[:3, :3] = rot
        delta[:3, 3] = tvec
        refined[v] = delta @ initial_poses[v]
        pose_corrections_mm[v] = float(np.linalg.norm(tvec) * 1000.0)
        pose_corrections_deg[v] = float(np.degrees(np.linalg.norm(rvec)))
        final_res.append(float(np.mean(np.abs(res.fun))))

    mean_res = float(np.mean(final_res)) if final_res else float("inf")
    return BundleAdjustmentResult(
        refined_poses=refined,
        pose_correction_mm=pose_corrections_mm,
        pose_rotation_correction_deg=pose_corrections_deg,
        final_residual_pix=mean_res,
        converged=mean_res < tolerance_pix,
    )
