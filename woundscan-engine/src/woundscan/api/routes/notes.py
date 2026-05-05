"""Visit note generation + retrieval.

Notes are produced from objective measurements + clinician-entered wound
bed characterization. The body text, sha256, and template version are
all stored so audits can prove the as-signed text was generated from a
specific data snapshot.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from woundscan.api.audit import get_audit_logger
from woundscan.api.auth import get_identity
from woundscan.api.routes.measurements import _RESPONSE_CACHE
from woundscan.auth.audit_log import AuditAction, AuditLogger
from woundscan.auth.identity import Identity
from woundscan.billing.medicare import (
    GPCI,
    PlaceOfService,
    estimate_reimbursement,
)
from woundscan.notes.generator import (
    GraftRecord,
    NoteContext,
    ProgressionDelta,
    generate_progression_note,
)

router = APIRouter(prefix="/notes", tags=["notes"])

_NOTES: dict[UUID, dict] = {}


class GraftRecordIn(BaseModel):
    product_name: str
    serial_number: str
    lot_number: str
    expiration_date: date
    applied_area_cm2: float = Field(..., gt=0)
    package_size_cm2: float = Field(..., gt=0)


class ReimbursementHints(BaseModel):
    anatomic_region: str = Field(..., pattern="^(trunk_arms_legs|face_scalp_digits)$")
    pos_code: str = Field("11", min_length=2, max_length=2)
    drug_asp_per_cm2: float = 0.0
    gpci_work: float = 1.0
    gpci_pe: float = 1.0
    gpci_mp: float = 1.0


class GenerateNoteIn(BaseModel):
    measurement_id: UUID
    anatomic_location: str
    wound_type: str
    patient_token: str

    # Subjective
    tissue_types: dict[str, float] = Field(default_factory=dict)
    drainage_amount: str = "scant"
    drainage_quality: str = "serous"
    odor: str = "none"
    periwound_status: str = "intact"
    pain_level_0_10: int = Field(0, ge=0, le=10)

    # Optional progression delta — supplied by caller from prior measurement
    days_since_prior: int | None = None
    prior_volume_cm3: float | None = None
    prior_area_cm2: float | None = None
    prior_max_depth_cm: float | None = None

    grafts_applied: list[GraftRecordIn] = Field(default_factory=list)
    reimbursement_hints: ReimbursementHints | None = None
    clinician_addendum: str = ""


class NoteOut(BaseModel):
    id: UUID
    wound_id: UUID
    measurement_id: UUID
    organization_id: UUID
    authored_by: UUID
    authored_at: datetime
    template_version: str
    body_text: str
    body_sha256: str
    is_signed: bool
    signed_at: datetime | None
    metadata: dict


def _delta(req: GenerateNoteIn, vol: float, area: float, depth: float) -> ProgressionDelta | None:
    if req.days_since_prior is None:
        return None
    pv = req.prior_volume_cm3
    pa = req.prior_area_cm2
    pd = req.prior_max_depth_cm
    return ProgressionDelta(
        days_since_prior=req.days_since_prior,
        prior_volume_cm3=pv,
        prior_area_cm2=pa,
        prior_max_depth_cm=pd,
        volume_change_cm3=(vol - pv) if pv is not None else None,
        area_change_cm2=(area - pa) if pa is not None else None,
        depth_change_cm=(depth - pd) if pd is not None else None,
        pct_volume_change=((vol - pv) / pv * 100.0) if pv else None,
        pct_area_change=((area - pa) / pa * 100.0) if pa else None,
    )


@router.post("", response_model=NoteOut, status_code=201)
def generate_note(
    req: GenerateNoteIn,
    identity: Identity = Depends(get_identity),
    audit: AuditLogger = Depends(get_audit_logger),
) -> NoteOut:
    measurement = _RESPONSE_CACHE.get(req.measurement_id)
    if measurement is None:
        raise HTTPException(status_code=404, detail="Measurement not found")

    delta = _delta(
        req,
        vol=measurement.volume.mean,
        area=measurement.surface_area.mean,
        depth=measurement.max_depth_cm,
    )

    grafts = [
        GraftRecord(
            product_name=g.product_name,
            serial_number=g.serial_number,
            lot_number=g.lot_number,
            expiration_date=g.expiration_date,
            applied_area_cm2=g.applied_area_cm2,
            package_size_cm2=g.package_size_cm2,
        )
        for g in req.grafts_applied
    ]

    reimbursement = None
    if req.reimbursement_hints and grafts:
        total_applied = sum(g.applied_area_cm2 for g in grafts)
        max_pkg = max((g.package_size_cm2 for g in grafts), default=None)
        reimbursement = estimate_reimbursement(
            applied_area_cm2=total_applied,
            anatomic_region=req.reimbursement_hints.anatomic_region,
            pos=PlaceOfService(req.reimbursement_hints.pos_code),
            gpci=GPCI(
                work=req.reimbursement_hints.gpci_work,
                practice_expense=req.reimbursement_hints.gpci_pe,
                malpractice=req.reimbursement_hints.gpci_mp,
            ),
            drug_asp_per_cm2=req.reimbursement_hints.drug_asp_per_cm2,
            package_size_cm2=max_pkg,
        )

    ctx = NoteContext(
        patient_token=req.patient_token,
        wound_id=str(measurement.wound_id),
        measurement_id=str(measurement.measurement_id),
        captured_at=measurement.captured_at,
        anatomic_location=req.anatomic_location,
        wound_type=req.wound_type,
        volume_cm3=measurement.volume.mean,
        surface_area_cm2=measurement.surface_area.mean,
        max_depth_cm=measurement.max_depth_cm,
        mean_depth_cm=measurement.mean_depth_cm,
        perimeter_cm=measurement.perimeter_cm,
        quality_grade=measurement.quality.grade,
        tissue_types=req.tissue_types,
        drainage_amount=req.drainage_amount,
        drainage_quality=req.drainage_quality,
        odor=req.odor,
        periwound_status=req.periwound_status,
        pain_level_0_10=req.pain_level_0_10,
        progression=delta,
        grafts_applied=grafts,
        reimbursement=reimbursement,
        clinician_addendum=req.clinician_addendum,
    )

    body, sha, meta = generate_progression_note(ctx)
    note = NoteOut(
        id=uuid4(),
        wound_id=measurement.wound_id,
        measurement_id=measurement.measurement_id,
        organization_id=identity.organization_id,
        authored_by=identity.user_id,
        authored_at=datetime.now(UTC),
        template_version=meta["template_version"],
        body_text=body,
        body_sha256=sha,
        is_signed=False,
        signed_at=None,
        metadata=meta,
    )
    _NOTES[note.id] = note.model_dump()

    audit.log(
        action=AuditAction.CREATE_MEASUREMENT,
        user_id=identity.user_id,
        organization_id=identity.organization_id,
        resource_type="progression_note",
        resource_id=str(note.id),
        metadata={"measurement_id": str(measurement.measurement_id), "sha256": sha},
    )
    return note


@router.post("/{note_id}/sign", response_model=NoteOut)
def sign_note(
    note_id: UUID,
    identity: Identity = Depends(get_identity),
    audit: AuditLogger = Depends(get_audit_logger),
) -> NoteOut:
    """Affix the clinician's electronic signature. Once signed, edits
    create an amendment (new note with amends_note_id pointer)."""
    n = _NOTES.get(note_id)
    if n is None or n["organization_id"] != identity.organization_id:
        raise HTTPException(status_code=404, detail="Note not found")
    if n["is_signed"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Note already signed; create an amendment instead.",
        )
    n["is_signed"] = True
    n["signed_at"] = datetime.now(UTC)
    audit.log(
        action=AuditAction.SIGN_OFF_MEASUREMENT,
        user_id=identity.user_id,
        organization_id=identity.organization_id,
        resource_type="progression_note",
        resource_id=str(note_id),
    )
    return NoteOut(**n)


@router.get("", response_model=list[NoteOut])
def list_notes(
    wound_id: UUID | None = None,
    identity: Identity = Depends(get_identity),
) -> list[NoteOut]:
    rows = [
        NoteOut(**n) for n in _NOTES.values()
        if n["organization_id"] == identity.organization_id
        and (wound_id is None or n["wound_id"] == wound_id)
    ]
    return sorted(rows, key=lambda n: n.authored_at, reverse=True)
