"""Fusion: combine LiDAR, RGB, and probe measurements into a single depth surface."""
from __future__ import annotations

from woundscan.fusion.bundle_adjustment import (
    BundleAdjustmentResult,
    run_bundle_adjustment,
)
from woundscan.fusion.force_correction import (
    ForceCorrectionTable,
    apply_force_correction,
    default_correction_table,
)
from woundscan.fusion.gaussian_process import GPFusionResult, fuse_gaussian_process
from woundscan.fusion.interpolation import thin_plate_spline
from woundscan.fusion.temporal import TemporalState, TemporalUpdate, kalman_update

__all__ = [
    "BundleAdjustmentResult",
    "ForceCorrectionTable",
    "GPFusionResult",
    "TemporalState",
    "TemporalUpdate",
    "apply_force_correction",
    "default_correction_table",
    "fuse_gaussian_process",
    "kalman_update",
    "run_bundle_adjustment",
    "thin_plate_spline",
]
