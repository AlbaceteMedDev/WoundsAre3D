"""Medicare reimbursement estimator for skin substitute graft applications.

This is a *defensible estimator*, not a billing system of record. Real
adjudication happens at the payer. We use the public components:

  * **Physician Fee Schedule (PFS) RVUs** for the application code (CPT
    15271-15278 for skin substitutes; the RVU we apply depends on
    site-of-service).
  * **Locality wage index** (Geographic Practice Cost Indices) — Work,
    Practice Expense, Malpractice — applied to the corresponding RVU.
  * **CMS conversion factor** (annual; we read from a settings table).
  * **Place-of-Service modifier**: facility (POS 22, 19, 21) uses the
    facility PE RVU; non-facility (POS 11) uses the non-facility PE RVU.
    The two differ materially because the office bears overhead.
  * **Q-code drug payment** for the actual graft material — paid at ASP
    + 6% per CMS rules. We expose product-level rates from the product DB.

The output reports per-application total + 12-month projected revenue if
graft frequency holds. We do NOT promise fee-for-service reimbursement;
MA plans and HOPPS bundling can override.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class PlaceOfService(StrEnum):
    """CMS Place-of-Service codes relevant for wound care."""

    OFFICE = "11"  # Physician office — non-facility rate (higher PE)
    OUTPATIENT = "22"  # Hospital outpatient — facility rate
    EMERGENCY = "23"  # Emergency dept — facility rate
    HOSPITAL_INPATIENT = "21"
    SNF = "31"  # Skilled Nursing Facility
    HOME = "12"  # Home — non-facility rate
    URGENT_CARE = "20"  # Urgent care — non-facility rate

    @property
    def is_facility(self) -> bool:
        """Facility POS uses the facility PE RVU (lower)."""
        return self in {
            PlaceOfService.OUTPATIENT,
            PlaceOfService.EMERGENCY,
            PlaceOfService.HOSPITAL_INPATIENT,
            PlaceOfService.SNF,
        }


@dataclass(frozen=True)
class CPTRow:
    """Per-CPT RVU components from CMS PFS (annual)."""

    code: str
    description: str
    work_rvu: float
    pe_rvu_facility: float
    pe_rvu_non_facility: float
    mp_rvu: float


# CMS PFS 2025 final rule values for the most common skin-substitute
# application codes. Source: CY 2025 PFS Final Rule, Addenda B & C.
# Update annually — the conversion factor and RVUs change each January.
_CPT_TABLE: dict[str, CPTRow] = {
    "15271": CPTRow(
        code="15271",
        description="Skin sub graft, trunk/arms/legs, first 25 cm² or less",
        work_rvu=0.86,
        pe_rvu_facility=0.65,
        pe_rvu_non_facility=4.39,
        mp_rvu=0.06,
    ),
    "15272": CPTRow(
        code="15272",
        description="Skin sub graft, trunk/arms/legs, each addl 25 cm²",
        work_rvu=0.27,
        pe_rvu_facility=0.16,
        pe_rvu_non_facility=0.97,
        mp_rvu=0.02,
    ),
    "15273": CPTRow(
        code="15273",
        description="Skin sub graft, trunk/arms/legs, first 100 cm² (peds/infants)",
        work_rvu=2.00,
        pe_rvu_facility=1.40,
        pe_rvu_non_facility=8.10,
        mp_rvu=0.16,
    ),
    "15275": CPTRow(
        code="15275",
        description="Skin sub graft, face/scalp/digits, first 25 cm² or less",
        work_rvu=1.50,
        pe_rvu_facility=1.05,
        pe_rvu_non_facility=5.10,
        mp_rvu=0.10,
    ),
    "15276": CPTRow(
        code="15276",
        description="Skin sub graft, face/scalp/digits, each addl 25 cm²",
        work_rvu=0.50,
        pe_rvu_facility=0.30,
        pe_rvu_non_facility=1.20,
        mp_rvu=0.04,
    ),
}


# CMS 2025 PFS conversion factor (dollars per total-RVU). Subject to
# annual update; override via reimbursement_settings if mid-year change.
DEFAULT_CONVERSION_FACTOR_2025 = 32.3465


@dataclass
class GPCI:
    """Geographic Practice Cost Indices for a locality."""

    work: float = 1.0
    practice_expense: float = 1.0
    malpractice: float = 1.0


@dataclass
class MedicareEstimate:
    """Result of one application's reimbursement calculation."""

    pos: PlaceOfService
    primary_cpt: str
    additional_cpt_units: int
    primary_cpt_payment: float
    additional_units_payment: float
    drug_payment: float
    total_payment: float
    breakdown: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def _cpt_payment(
    code: str,
    pos: PlaceOfService,
    gpci: GPCI,
    conversion_factor: float,
) -> tuple[float, dict[str, float]]:
    row = _CPT_TABLE.get(code)
    if row is None:
        raise ValueError(f"Unknown CPT code: {code}")
    pe_rvu = row.pe_rvu_facility if pos.is_facility else row.pe_rvu_non_facility
    work_paid = row.work_rvu * gpci.work
    pe_paid = pe_rvu * gpci.practice_expense
    mp_paid = row.mp_rvu * gpci.malpractice
    total_rvu = work_paid + pe_paid + mp_paid
    payment = total_rvu * conversion_factor
    breakdown = {
        "work_rvu_adjusted": round(work_paid, 4),
        "pe_rvu_adjusted": round(pe_paid, 4),
        "mp_rvu_adjusted": round(mp_paid, 4),
        "total_rvu": round(total_rvu, 4),
        "conversion_factor": conversion_factor,
        "payment": round(payment, 2),
    }
    return payment, breakdown


def estimate_reimbursement(
    *,
    applied_area_cm2: float,
    anatomic_region: str,  # "trunk_arms_legs" or "face_scalp_digits"
    pos: PlaceOfService,
    gpci: GPCI,
    drug_asp_per_cm2: float = 0.0,  # graft material's CMS ASP+6% per cm² (Q-code)
    package_size_cm2: float | None = None,  # if set, reimburse on whole-package
    conversion_factor: float = DEFAULT_CONVERSION_FACTOR_2025,
) -> MedicareEstimate:
    """Estimate per-application Medicare allowed amount.

    The total-area code billing model:
      * Pick the *primary* code (15271 or 15275) for the first 25 cm² (or
        first 100 cm² for the pediatric variants — caller selects).
      * Each additional 25 cm² (or fraction) bills the *add-on* code
        (15272 or 15276) once. CMS rounds up: 26 cm² → 1 add-on unit.
      * Drug Q-code is billed on units actually used, but CMS waste rules
        reimburse single-use packages on the whole package size.

    Returns dollars allowed (Medicare's 80% share + the patient's 20%
    coinsurance — total allowed amount, not just the program payment).
    """
    if applied_area_cm2 <= 0:
        raise ValueError("applied_area_cm2 must be positive")

    if anatomic_region == "trunk_arms_legs":
        primary, addon = "15271", "15272"
    elif anatomic_region == "face_scalp_digits":
        primary, addon = "15275", "15276"
    else:
        raise ValueError(f"Unknown anatomic_region: {anatomic_region}")

    primary_payment, primary_bd = _cpt_payment(primary, pos, gpci, conversion_factor)

    extra_cm2 = max(0.0, applied_area_cm2 - 25.0)
    addon_units = int(-(-extra_cm2 // 25))  # ceil
    addon_unit_payment, addon_bd = _cpt_payment(addon, pos, gpci, conversion_factor)
    additional_payment = addon_unit_payment * addon_units

    # CMS reimburses single-use skin-substitute packages on the *package*
    # size (waste documentation rule). If a 100 cm² package was opened
    # for a 60 cm² wound, 100 cm² of drug is reimbursable.
    drug_billable_cm2 = package_size_cm2 if package_size_cm2 else applied_area_cm2
    drug_payment = drug_billable_cm2 * drug_asp_per_cm2

    total = primary_payment + additional_payment + drug_payment

    notes = []
    if package_size_cm2 and package_size_cm2 > applied_area_cm2:
        waste = package_size_cm2 - applied_area_cm2
        notes.append(
            f"Wastage modifier (-JW) required: {waste:.1f} cm² discarded; "
            f"CMS reimburses whole-package size for single-use skin substitutes."
        )
    if pos.is_facility:
        notes.append(
            "Facility POS — practice-expense RVU set to facility rate; "
            "practice does not bill overhead component."
        )

    return MedicareEstimate(
        pos=pos,
        primary_cpt=primary,
        additional_cpt_units=addon_units,
        primary_cpt_payment=round(primary_payment, 2),
        additional_units_payment=round(additional_payment, 2),
        drug_payment=round(drug_payment, 2),
        total_payment=round(total, 2),
        breakdown={
            "primary_cpt_breakdown": primary_bd,
            "addon_cpt_breakdown": addon_bd,
            "addon_units": addon_units,
            "drug_billable_cm2": round(drug_billable_cm2, 2),
            "drug_asp_per_cm2": drug_asp_per_cm2,
        },
        notes=notes,
    )
