"""Pydantic models for measurement requests / responses."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ProbeMeasurementInput(BaseModel):
    """A single probe-anchor entry from the iOS app."""

    x_mm: float
    y_mm: float
    depth_mm: float = Field(..., ge=0.0)
    force_category: str = Field(..., pattern="^(light|medium|firm)$")
    probe_type: str = Field("cotton_tip", pattern="^(cotton_tip|plastic_gauge|kundin_gauge|other)$")
    auto_detected: bool = False
    notes: str = ""


class FiducialDetectionInput(BaseModel):
    marker_id: int
    corners_pix: list[list[float]]
    rvec: list[float] = Field(..., min_length=3, max_length=3)
    tvec: list[float] = Field(..., min_length=3, max_length=3)
    reprojection_error_pix: float


class CameraIntrinsicsInput(BaseModel):
    fx: float
    fy: float
    cx: float
    cy: float
    width: int
    height: int


class CapturePoseInput(BaseModel):
    position_m: list[float] = Field(..., min_length=3, max_length=3)
    rotation_quat: list[float] = Field(..., min_length=4, max_length=4)
    timestamp_s: float


class WoundBoundaryInput(BaseModel):
    """Polygon vertices in mm in the wound-local frame."""

    vertices_mm: list[list[float]]

    @field_validator("vertices_mm")
    @classmethod
    def at_least_3_vertices(cls, v: list[list[float]]) -> list[list[float]]:
        if len(v) < 3:
            raise ValueError("Need at least 3 vertices")
        return v


class CreateMeasurementRequest(BaseModel):
    """Inbound multi-modal capture payload from the iOS app.

    Heavy binary fields (depth maps, RGB images) are NOT inlined here;
    the iOS app uploads them to S3 directly with presigned URLs and
    references them by key. This payload references those keys.
    """

    wound_id: UUID
    captured_at: datetime
    intrinsics: CameraIntrinsicsInput
    rgb_s3_key: str
    depth_burst_s3_keys: list[str]
    poses: list[CapturePoseInput]
    fiducials: list[FiducialDetectionInput]
    fiducial_marker_side_mm: float
    fiducial_separation_mm: float
    boundary: WoundBoundaryInput
    probe_measurements: list[ProbeMeasurementInput]
    overlap_delta_cm: float | None = None
    selected_product_ids: list[str] = Field(default_factory=list)
    polarized_capture_s3_key: str | None = None
    multispectral_capture_s3_keys: list[str] = Field(default_factory=list)
    days_since_last_visit: float | None = None
    last_volume_cm3: float | None = None
    last_area_cm2: float | None = None


class UncertaintyValue(BaseModel):
    mean: float
    std: float
    ci_95_low: float
    ci_95_high: float


class GraftRecommendationOut(BaseModel):
    product_id: str
    product_name: str
    overlap_delta_cm: float
    required_cm2: float
    selected_size_cm2: float | None
    rationale: str


class QualityReportOut(BaseModel):
    grade: str
    overall_score: float
    components: dict[str, float]
    recommendation: str


class MeasurementResponse(BaseModel):
    """Outbound measurement result."""

    measurement_id: UUID
    wound_id: UUID
    captured_at: datetime
    processed_at: datetime
    processing_duration_ms: float
    volume: UncertaintyValue
    surface_area: UncertaintyValue
    max_depth_cm: float
    mean_depth_cm: float
    perimeter_cm: float
    footprint_area_cm2: float
    quality: QualityReportOut
    graft_recommendations: list[GraftRecommendationOut]
    plausibility_passed: bool
    plausibility_warnings: list[str]
    temporal_warnings: list[str]
    pdf_s3_key: str
    provenance: dict
