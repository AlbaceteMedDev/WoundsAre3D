"""Composite A/B/C/F quality grading for each measurement.

Inputs:
- Mean confidence across wound bed (from quality.confidence_map)
- Number and quality of physical anchor points
- Camera-probe agreement
- Fiducial detection success and pose error
- Photo quality metrics (resolution, focus)
- Frame consistency
- ML segmentation confidence

Output:
- Letter grade A/B/C/F
- Per-component sub-score
- Recommended action (proceed / review / recapture)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class QualityGrade(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    F = "F"


@dataclass(frozen=True)
class QualityReport:
    """Quality grade with full sub-score breakdown.

    Attributes
    ----------
    grade : QualityGrade
    overall_score : float in [0, 1]
    components : dict[str, float]
    recommendation : str
        "proceed", "review_with_caution", "recapture_recommended"
    """

    grade: QualityGrade
    overall_score: float
    components: dict[str, float]
    recommendation: str


def _grade_from_score(score: float) -> QualityGrade:
    if score >= 0.85:
        return QualityGrade.A
    if score >= 0.70:
        return QualityGrade.B
    if score >= 0.50:
        return QualityGrade.C
    return QualityGrade.F


def _recommendation(grade: QualityGrade) -> str:
    return {
        QualityGrade.A: "proceed",
        QualityGrade.B: "proceed",
        QualityGrade.C: "review_with_caution",
        QualityGrade.F: "recapture_recommended",
    }[grade]


def compute_quality_grade(
    mean_confidence: float,
    n_probe_anchors: int,
    camera_probe_max_z: float,
    fiducial_detected_count: int,
    fiducial_max_reprojection_pix: float,
    frame_consistency_mean: float,
    ml_segmentation_confidence: float,
    photo_focus_score: float = 1.0,
) -> QualityReport:
    """Compute composite quality grade from sub-component scores."""

    # Map each component to [0, 1]
    confidence_score = max(0.0, min(1.0, mean_confidence))

    # 9 anchors recommended; 5 minimum; below 5 -> 0; at 9 -> 1; above 9 -> 1
    if n_probe_anchors < 5:
        anchor_score = max(0.0, n_probe_anchors / 5.0 * 0.5)
    else:
        anchor_score = min(1.0, 0.5 + (n_probe_anchors - 5) / 8.0)

    # Camera-probe agreement: z<=1 -> 1, z>=4 -> 0
    cp_score = max(0.0, min(1.0, 1.0 - (camera_probe_max_z - 1.0) / 3.0))

    # Fiducials: 4 -> 1, 0 -> 0
    fid_count_score = min(1.0, fiducial_detected_count / 4.0)
    # Reprojection: <=1px ideal, >=5px bad
    fid_reproj_score = max(0.0, min(1.0, 1.0 - (fiducial_max_reprojection_pix - 1.0) / 4.0))
    fid_score = 0.5 * fid_count_score + 0.5 * fid_reproj_score

    fc_score = max(0.0, min(1.0, frame_consistency_mean))
    ml_score = max(0.0, min(1.0, ml_segmentation_confidence))
    focus_score = max(0.0, min(1.0, photo_focus_score))

    components = {
        "mean_confidence": confidence_score,
        "anchor_count_quality": anchor_score,
        "camera_probe_agreement": cp_score,
        "fiducial_quality": fid_score,
        "frame_consistency": fc_score,
        "ml_segmentation": ml_score,
        "photo_focus": focus_score,
    }

    weights = {
        "mean_confidence": 0.25,
        "anchor_count_quality": 0.20,
        "camera_probe_agreement": 0.15,
        "fiducial_quality": 0.15,
        "frame_consistency": 0.10,
        "ml_segmentation": 0.10,
        "photo_focus": 0.05,
    }
    overall = sum(components[k] * weights[k] for k in components)

    grade = _grade_from_score(overall)
    return QualityReport(
        grade=grade,
        overall_score=overall,
        components=components,
        recommendation=_recommendation(grade),
    )
