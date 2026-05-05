"""Graft application endpoints — UDI-traceable physical grafts applied to wounds.

Each application captures the FDA Unique Device Identifier components
(serial number, lot number, expiration date) so we can support audits,
recalls, and inventory reconciliation.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from woundscan.api.audit import get_audit_logger
from woundscan.api.auth import get_identity
from woundscan.auth.audit_log import AuditAction, AuditLogger
from woundscan.auth.identity import Identity

router = APIRouter(prefix="/grafts", tags=["grafts"])


# In-memory store for the dev path. Production wires this to the
# graft_applications Postgres table via SQLAlchemy.
_GRAFTS: dict[UUID, dict] = {}


class GraftApplicationIn(BaseModel):
    wound_id: UUID
    measurement_id: UUID | None = None
    product_id: str
    product_name: str
    udi_di: str | None = None
    serial_number: str = Field(..., min_length=1)
    lot_number: str = Field(..., min_length=1)
    expiration_date: date
    manufacture_date: date | None = None
    package_size_cm2: float = Field(..., gt=0)
    applied_area_cm2: float = Field(..., gt=0)
    waste_area_cm2: float = Field(0.0, ge=0)
    hcpcs_code: str | None = None
    cpt_code: str | None = None
    notes: str = ""


class GraftApplicationOut(BaseModel):
    id: UUID
    wound_id: UUID
    measurement_id: UUID | None
    organization_id: UUID
    applied_by: UUID
    applied_at: datetime
    product_id: str
    product_name: str
    udi_di: str | None
    serial_number: str
    lot_number: str
    expiration_date: date
    manufacture_date: date | None
    package_size_cm2: float
    applied_area_cm2: float
    waste_area_cm2: float
    hcpcs_code: str | None
    cpt_code: str | None
    notes: str


def _check_expiration(exp: date) -> None:
    if exp < date.today():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Graft is expired (expiration_date={exp.isoformat()}); "
            "applying expired skin substitute is not billable.",
        )


@router.post("/applications", response_model=GraftApplicationOut, status_code=201)
def create_application(
    req: GraftApplicationIn,
    identity: Identity = Depends(get_identity),
    audit: AuditLogger = Depends(get_audit_logger),
) -> GraftApplicationOut:
    """Record a graft application against a wound.

    The serial_number + lot_number + expiration_date triplet is the
    production identifier (PI) component of FDA UDI; the udi_di is the
    static device identifier from the package. Together they uniquely
    identify which physical unit of skin substitute was placed on which
    wound, supporting recall traceability per 21 CFR 830.
    """
    _check_expiration(req.expiration_date)
    if req.applied_area_cm2 > req.package_size_cm2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="applied_area_cm2 cannot exceed package_size_cm2",
        )
    waste = req.waste_area_cm2 or max(0.0, req.package_size_cm2 - req.applied_area_cm2)

    out = GraftApplicationOut(
        id=uuid4(),
        wound_id=req.wound_id,
        measurement_id=req.measurement_id,
        organization_id=identity.organization_id,
        applied_by=identity.user_id,
        applied_at=datetime.now(UTC),
        product_id=req.product_id,
        product_name=req.product_name,
        udi_di=req.udi_di,
        serial_number=req.serial_number,
        lot_number=req.lot_number,
        expiration_date=req.expiration_date,
        manufacture_date=req.manufacture_date,
        package_size_cm2=req.package_size_cm2,
        applied_area_cm2=req.applied_area_cm2,
        waste_area_cm2=waste,
        hcpcs_code=req.hcpcs_code,
        cpt_code=req.cpt_code,
        notes=req.notes,
    )
    _GRAFTS[out.id] = out.model_dump()

    audit.log(
        action=AuditAction.CREATE_MEASUREMENT,  # reuse closest existing action
        user_id=identity.user_id,
        organization_id=identity.organization_id,
        resource_type="graft_application",
        resource_id=str(out.id),
        metadata={
            "wound_id": str(req.wound_id),
            "product_id": req.product_id,
            "serial_number": req.serial_number,
            "lot_number": req.lot_number,
            "expiration_date": req.expiration_date.isoformat(),
            "applied_area_cm2": req.applied_area_cm2,
        },
    )
    return out


@router.get("/applications", response_model=list[GraftApplicationOut])
def list_applications(
    wound_id: UUID | None = None,
    identity: Identity = Depends(get_identity),
) -> list[GraftApplicationOut]:
    """List graft applications, optionally filtered by wound."""
    rows = [
        GraftApplicationOut(**g)
        for g in _GRAFTS.values()
        if g["organization_id"] == identity.organization_id
    ]
    if wound_id is not None:
        rows = [r for r in rows if r.wound_id == wound_id]
    return sorted(rows, key=lambda r: r.applied_at, reverse=True)


@router.get("/applications/{application_id}", response_model=GraftApplicationOut)
def get_application(
    application_id: UUID,
    identity: Identity = Depends(get_identity),
) -> GraftApplicationOut:
    g = _GRAFTS.get(application_id)
    if g is None or g["organization_id"] != identity.organization_id:
        raise HTTPException(status_code=404, detail="Graft application not found")
    return GraftApplicationOut(**g)


@router.get("/inventory/expiring")
def list_expiring_inventory(
    days: int = 60,
    identity: Identity = Depends(get_identity),
) -> dict:
    """Roll-up of graft applications whose lots expire within `days`.

    Used by the inventory dashboard to flag stock that should be used or
    rotated. (Real inventory needs a separate stock-on-hand table; this
    endpoint reports applied units with imminent expirations as a proxy
    until that's wired.)
    """
    today = date.today()
    soon = [
        g
        for g in _GRAFTS.values()
        if g["organization_id"] == identity.organization_id
        and (g["expiration_date"] - today).days <= days
    ]
    return {
        "as_of": today.isoformat(),
        "horizon_days": days,
        "count": len(soon),
        "items": [
            {
                "product_name": g["product_name"],
                "serial_number": g["serial_number"],
                "lot_number": g["lot_number"],
                "expiration_date": g["expiration_date"].isoformat(),
                "days_to_expiration": (g["expiration_date"] - today).days,
            }
            for g in soon
        ],
    }
