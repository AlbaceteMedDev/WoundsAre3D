"""Wound CRUD endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
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
        created_at=datetime.now(timezone.utc),
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
