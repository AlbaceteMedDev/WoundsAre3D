"""Wound CRUD endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from woundscan.api.auth import get_identity
from woundscan.auth.identity import Identity

router = APIRouter(prefix="/wounds", tags=["wounds"])

_WOUNDS: dict[UUID, dict] = {}


class CreateWoundRequest(BaseModel):
    patient_token: str
    anatomic_location: str
    wound_type: str
    onset_at: datetime | None = None
    notes: str = ""


class WoundOut(BaseModel):
    id: UUID
    patient_token: str
    anatomic_location: str
    wound_type: str
    onset_at: datetime | None
    created_at: datetime
    notes: str


@router.post("", response_model=WoundOut, status_code=201)
def create_wound(req: CreateWoundRequest, identity: Identity = Depends(get_identity)) -> WoundOut:
    wid = uuid4()
    out = WoundOut(
        id=wid,
        patient_token=req.patient_token,
        anatomic_location=req.anatomic_location,
        wound_type=req.wound_type,
        onset_at=req.onset_at,
        created_at=datetime.now(UTC),
        notes=req.notes,
    )
    _WOUNDS[wid] = out.model_dump()
    return out


@router.get("/{wound_id}", response_model=WoundOut)
def get_wound(wound_id: UUID, identity: Identity = Depends(get_identity)) -> WoundOut:
    from fastapi import HTTPException

    if wound_id not in _WOUNDS:
        raise HTTPException(status_code=404, detail="Wound not found")
    return WoundOut(**_WOUNDS[wound_id])


@router.get("", response_model=list[WoundOut])
def list_wounds(identity: Identity = Depends(get_identity)) -> list[WoundOut]:
    return [WoundOut(**v) for v in _WOUNDS.values()]


class ProgressionPoint(BaseModel):
    measurement_id: UUID
    captured_at: datetime
    volume_cm3: float
    surface_area_cm2: float
    max_depth_cm: float
    mean_depth_cm: float
    perimeter_cm: float
    quality_grade: str


class ProgressionTrend(BaseModel):
    """Summary of healing trajectory over the captured series."""

    first_capture_at: datetime | None
    last_capture_at: datetime | None
    days_observed: int
    initial_area_cm2: float | None
    latest_area_cm2: float | None
    pct_area_change: float | None
    initial_volume_cm3: float | None
    latest_volume_cm3: float | None
    pct_volume_change: float | None
    healing_rate_cm2_per_week: float | None
    is_healing: bool
    is_stalled: bool


class ProgressionResponse(BaseModel):
    wound_id: UUID
    points: list[ProgressionPoint]
    trend: ProgressionTrend


@router.get("/{wound_id}/progression", response_model=ProgressionResponse)
def get_progression(
    wound_id: UUID,
    identity: Identity = Depends(get_identity),
) -> ProgressionResponse:
    """Time-series of measurements for a single wound, with trend summary.

    The trend block is what the portal renders as the headline (healing /
    stalled / worsening); points feed the chart. A wound is "healing" if
    surface area has decreased ≥10% since the first capture; "stalled" if
    the latest two captures span ≥21 days with <5% area change.
    """
    from woundscan.api.routes.measurements import _RESPONSE_CACHE

    points: list[ProgressionPoint] = []
    for m in _RESPONSE_CACHE.values():
        if m.wound_id != wound_id:
            continue
        points.append(
            ProgressionPoint(
                measurement_id=m.measurement_id,
                captured_at=m.captured_at,
                volume_cm3=m.volume.mean,
                surface_area_cm2=m.surface_area.mean,
                max_depth_cm=m.max_depth_cm,
                mean_depth_cm=m.mean_depth_cm,
                perimeter_cm=m.perimeter_cm,
                quality_grade=m.quality.grade,
            )
        )
    points.sort(key=lambda p: p.captured_at)

    trend = _compute_trend(points)
    return ProgressionResponse(wound_id=wound_id, points=points, trend=trend)


def _compute_trend(points: list[ProgressionPoint]) -> ProgressionTrend:
    if not points:
        return ProgressionTrend(
            first_capture_at=None, last_capture_at=None, days_observed=0,
            initial_area_cm2=None, latest_area_cm2=None, pct_area_change=None,
            initial_volume_cm3=None, latest_volume_cm3=None, pct_volume_change=None,
            healing_rate_cm2_per_week=None, is_healing=False, is_stalled=False,
        )
    first, last = points[0], points[-1]
    days = max((last.captured_at - first.captured_at).days, 0)

    pct_area = None
    pct_vol = None
    rate = None
    if first.surface_area_cm2 > 0:
        pct_area = (last.surface_area_cm2 - first.surface_area_cm2) / first.surface_area_cm2 * 100.0
        if days > 0:
            rate = (first.surface_area_cm2 - last.surface_area_cm2) / (days / 7.0)
    if first.volume_cm3 > 0:
        pct_vol = (last.volume_cm3 - first.volume_cm3) / first.volume_cm3 * 100.0

    is_healing = pct_area is not None and pct_area <= -10.0
    is_stalled = False
    if len(points) >= 2:
        recent_window_days = (last.captured_at - points[-2].captured_at).days
        if recent_window_days >= 21 and points[-2].surface_area_cm2 > 0:
            recent_pct = (
                (last.surface_area_cm2 - points[-2].surface_area_cm2)
                / points[-2].surface_area_cm2 * 100.0
            )
            if abs(recent_pct) < 5.0:
                is_stalled = True

    return ProgressionTrend(
        first_capture_at=first.captured_at,
        last_capture_at=last.captured_at,
        days_observed=days,
        initial_area_cm2=first.surface_area_cm2,
        latest_area_cm2=last.surface_area_cm2,
        pct_area_change=pct_area,
        initial_volume_cm3=first.volume_cm3,
        latest_volume_cm3=last.volume_cm3,
        pct_volume_change=pct_vol,
        healing_rate_cm2_per_week=rate,
        is_healing=is_healing,
        is_stalled=is_stalled,
    )
