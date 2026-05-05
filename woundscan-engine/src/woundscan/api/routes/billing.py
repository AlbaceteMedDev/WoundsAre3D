"""Reimbursement estimator endpoints.

A defensible *estimator*, not a billing system of record. We compute
the Medicare allowed amount (program payment + patient coinsurance)
using public CMS data: PFS RVUs, locality GPCI, conversion factor, and
ASP+6% for the drug Q-code.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from woundscan.api.auth import get_identity
from woundscan.auth.identity import Identity
from woundscan.billing.medicare import (
    DEFAULT_CONVERSION_FACTOR_2025,
    GPCI,
    PlaceOfService,
    estimate_reimbursement,
)

router = APIRouter(prefix="/reimbursement", tags=["reimbursement"])


class ReimbursementIn(BaseModel):
    applied_area_cm2: float = Field(..., gt=0)
    anatomic_region: str = Field(..., pattern="^(trunk_arms_legs|face_scalp_digits)$")
    pos_code: str = Field(..., min_length=2, max_length=2)
    package_size_cm2: float | None = None
    drug_asp_per_cm2: float = Field(0.0, ge=0)
    gpci_work: float = Field(1.0, gt=0)
    gpci_pe: float = Field(1.0, gt=0)
    gpci_mp: float = Field(1.0, gt=0)
    conversion_factor: float | None = None


class ReimbursementOut(BaseModel):
    pos: str
    primary_cpt: str
    additional_cpt_units: int
    primary_cpt_payment: float
    additional_units_payment: float
    drug_payment: float
    total_payment: float
    breakdown: dict
    notes: list[str]


@router.post("/calculate", response_model=ReimbursementOut)
def calculate(
    req: ReimbursementIn,
    identity: Identity = Depends(get_identity),
) -> ReimbursementOut:
    """Estimate Medicare allowed amount for one graft application.

    Inputs:
      - `applied_area_cm2`: actual wound area covered.
      - `anatomic_region`: drives CPT code family (15271/2 vs 15275/6).
      - `pos_code`: CMS Place-of-Service ("11" office, "22" outpatient, …).
      - `package_size_cm2`: if a single-use package was opened, CMS
        reimburses the whole package (waste billing). Pass the package
        size to apply that rule; omit for as-applied.
      - `drug_asp_per_cm2`: CMS-published ASP+6% for the specific Q-code.
      - GPCI components: locality wage indices for work / PE / MP.

    Returns total allowed amount with full RVU + drug breakdown.
    """
    pos = PlaceOfService(req.pos_code)
    gpci = GPCI(work=req.gpci_work, practice_expense=req.gpci_pe, malpractice=req.gpci_mp)
    cf = req.conversion_factor or DEFAULT_CONVERSION_FACTOR_2025

    est = estimate_reimbursement(
        applied_area_cm2=req.applied_area_cm2,
        anatomic_region=req.anatomic_region,
        pos=pos,
        gpci=gpci,
        drug_asp_per_cm2=req.drug_asp_per_cm2,
        package_size_cm2=req.package_size_cm2,
        conversion_factor=cf,
    )
    return ReimbursementOut(
        pos=est.pos.value,
        primary_cpt=est.primary_cpt,
        additional_cpt_units=est.additional_cpt_units,
        primary_cpt_payment=est.primary_cpt_payment,
        additional_units_payment=est.additional_units_payment,
        drug_payment=est.drug_payment,
        total_payment=est.total_payment,
        breakdown=est.breakdown,
        notes=est.notes,
    )
