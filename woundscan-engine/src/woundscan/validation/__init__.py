"""Validation: consistency, plausibility, quality grading, phantom calibration."""
from __future__ import annotations

from woundscan.validation.consistency import (
    CameraProbeAgreement,
    check_camera_probe_agreement,
)
from woundscan.validation.phantom_calibration import (
    PhantomCalibration,
    PhantomScan,
    record_phantom_scan,
)
from woundscan.validation.plausibility import (
    PlausibilityCheck,
    run_geometric_plausibility_checks,
)
from woundscan.validation.quality_score import (
    QualityGrade,
    QualityReport,
    compute_quality_grade,
)
from woundscan.validation.temporal_plausibility import (
    TemporalPlausibilityCheck,
    check_temporal_plausibility,
)

__all__ = [
    "CameraProbeAgreement",
    "PhantomCalibration",
    "PhantomScan",
    "PlausibilityCheck",
    "QualityGrade",
    "QualityReport",
    "TemporalPlausibilityCheck",
    "check_camera_probe_agreement",
    "check_temporal_plausibility",
    "compute_quality_grade",
    "record_phantom_scan",
    "run_geometric_plausibility_checks",
]
