"""Phantom calibration submission endpoint."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from woundscan.api.auth import get_identity
from woundscan.auth.identity import Identity

router = APIRouter(prefix="/phantom", tags=["phantom"])

_PHANTOM_RECORDS: list[dict] = []


class PhantomScanIn(BaseModel):
    phantom_catalog_id: str
    measured_volume_cm3: float
    measured_surface_area_cm2: float
    true_volume_cm3: float
    true_surface_area_cm2: float
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


@router.post("")
def submit_phantom_scan(scan: PhantomScanIn, identity: Identity = Depends(get_identity)) -> dict:
    record = scan.model_dump()
    record["clinician_id"] = str(identity.user_id)
    _PHANTOM_RECORDS.append(record)
    err_v = abs(scan.measured_volume_cm3 - scan.true_volume_cm3) / max(
        abs(scan.true_volume_cm3), 1e-9
    )
    err_sa = abs(scan.measured_surface_area_cm2 - scan.true_surface_area_cm2) / max(
        abs(scan.true_surface_area_cm2), 1e-9
    )
    return {
        "status": "recorded",
        "volume_error_pct": err_v * 100.0,
        "surface_area_error_pct": err_sa * 100.0,
        "drift_alert": err_v > 0.03,
    }


@router.get("")
def list_phantom_scans(identity: Identity = Depends(get_identity)) -> dict:
    return {"records": _PHANTOM_RECORDS[-100:], "total": len(_PHANTOM_RECORDS)}
