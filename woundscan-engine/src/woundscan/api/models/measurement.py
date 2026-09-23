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


class UnderminingInput(BaseModel):
    """A clinician-probed undermining reading at a clock position.

    Undermining cannot be observed optically -- nothing sees under intact skin
    -- so these are entered by hand and every derived figure is labelled
    probe-derived rather than instrument-derived.
    """

    clock_position_hours: float = Field(..., gt=0.0, le=12.0)
    extent_mm: float = Field(..., ge=0.0, le=200.0)
    probe_type: str = Field("cotton_tip", pattern="^(cotton_tip|plastic_gauge|kundin_gauge|other)$")
    force_category: str = Field("light", pattern="^(light|medium|firm)$")


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
    undermining: list[UnderminingInput] = Field(default_factory=list)
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


class UnderminingOut(BaseModel):
    """Undermining derived from clinician probe readings, not from the scan."""

    measured: bool
    source: str = "clinician probe"
    undermined_area_cm2: float
    undermined_area_ci_95_low_cm2: float
    undermined_area_ci_95_high_cm2: float
    visible_area_cm2: float
    total_area_with_undermining_cm2: float
    undermined_volume_cm3: float
    undermined_volume_ci_95_low_cm3: float
    undermined_volume_ci_95_high_cm3: float
    max_extent_mm: float
    max_extent_clock_hours: float
    involved_clock_positions: list[float]
    pocket_height_mm: float
    pocket_height_basis: str
    n_measurements: int


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
    undermining: UnderminingOut
    graft_recommendations: list[GraftRecommendationOut]
    plausibility_passed: bool
    plausibility_warnings: list[str]
    temporal_warnings: list[str]
    pdf_s3_key: str
    provenance: dict
