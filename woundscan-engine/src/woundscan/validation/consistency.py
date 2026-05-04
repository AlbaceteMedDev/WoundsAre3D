"""Camera vs probe agreement checking.

At each probe-anchor location, we have two depth estimates:
- The camera-derived depth (LiDAR + multiframe averaged)
- The clinician's probe measurement

If they disagree by more than expected from their respective uncertainty
budgets, something is wrong: bad fiducial registration, probe at the
wrong location, or LiDAR confidence overstated.

We compute a per-anchor disagreement (in mm and in z-score units) and
flag the measurement if any anchor exceeds threshold.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CameraProbeAgreement:
    """Per-anchor agreement statistics.

    Attributes
    ----------
    n_anchors : int
    mean_abs_diff_mm : float
        Mean absolute difference across anchors.
    max_abs_diff_mm : float
        Maximum absolute difference at any anchor.
    z_scores : (n_anchors,) array
    overall_passed : bool
        True if max z-score below threshold.
    threshold_z : float
    """

    n_anchors: int
    mean_abs_diff_mm: float
    max_abs_diff_mm: float
    z_scores: np.ndarray
    overall_passed: bool
    threshold_z: float = 3.0


def check_camera_probe_agreement(
    probe_x_mm: np.ndarray,
    probe_y_mm: np.ndarray,
    probe_d_mm: np.ndarray,
    probe_sigma_mm: np.ndarray,
    camera_grid_x_mm: np.ndarray,
    camera_grid_y_mm: np.ndarray,
    camera_depth_mm: np.ndarray,
    camera_sigma_mm: np.ndarray,
    threshold_z: float = 3.0,
) -> CameraProbeAgreement:
    """Compare camera depth at each anchor to the probe measurement.

    The camera depth at the anchor is interpolated bilinearly from the
    grid; sigma is interpolated similarly.
    """
    from scipy.interpolate import RegularGridInterpolator

    if camera_grid_x_mm.ndim != 2:
        raise ValueError("camera_grid must be 2D meshgrid in mm")

    x_axis = camera_grid_x_mm[0, :]
    y_axis = camera_grid_y_mm[:, 0]

    interp_d = RegularGridInterpolator(
        (y_axis, x_axis), camera_depth_mm, method="linear", bounds_error=False, fill_value=np.nan
    )
    interp_s = RegularGridInterpolator(
        (y_axis, x_axis), camera_sigma_mm, method="linear", bounds_error=False, fill_value=np.nan
    )

    pts = np.column_stack([probe_y_mm, probe_x_mm])
    d_cam = interp_d(pts)
    s_cam = interp_s(pts)

    diffs = np.asarray(probe_d_mm) - d_cam
    combined_sigma = np.sqrt(np.asarray(probe_sigma_mm) ** 2 + s_cam**2)
    z = np.where(combined_sigma > 0, diffs / combined_sigma, 0.0)

    passed = bool(np.nanmax(np.abs(z)) <= threshold_z) if z.size > 0 else True
    abs_diffs = np.abs(diffs)
    return CameraProbeAgreement(
        n_anchors=int(probe_d_mm.size),
        mean_abs_diff_mm=float(np.nanmean(abs_diffs)) if abs_diffs.size else 0.0,
        max_abs_diff_mm=float(np.nanmax(abs_diffs)) if abs_diffs.size else 0.0,
        z_scores=z.astype(np.float64),
        overall_passed=passed,
        threshold_z=threshold_z,
    )
