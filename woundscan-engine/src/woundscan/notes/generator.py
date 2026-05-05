"""Generate audit-defensible visit notes from objective measurement data.

Notes are built from a deterministic template populated with measurement
deltas, wound bed characteristics, applied grafts, and clinician inputs.
The template version is recorded with the note so that future audits can
reproduce the exact text from raw data.

We deliberately keep this template-based (no LLM) so the output is
predictable, reviewable, and stable across deployments. A clinician can
override any field, and the diff is preserved in the audit log.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime

from woundscan.billing.medicare import MedicareEstimate


TEMPLATE_VERSION = "v1.2025.05"


@dataclass
class ProgressionDelta:
    """Week-over-week change versus the prior measurement."""

    days_since_prior: int
    prior_volume_cm3: float | None
    prior_area_cm2: float | None
    prior_max_depth_cm: float | None
    volume_change_cm3: float | None
    area_change_cm2: float | None
    depth_change_cm: float | None
    pct_volume_change: float | None
    pct_area_change: float | None

    @property
    def is_healing(self) -> bool:
        """Standard healing trajectory: 4+ wk to 50% area reduction."""
        return (self.pct_area_change is not None) and self.pct_area_change <= -10.0

    @property
    def is_worsening(self) -> bool:
        return (self.pct_area_change is not None) and self.pct_area_change >= 10.0


@dataclass
class GraftRecord:
    product_name: str
    serial_number: str
    lot_number: str
    expiration_date: date
    applied_area_cm2: float
    package_size_cm2: float


@dataclass
class NoteContext:
    """All inputs for a visit note. All fields are objective + audit-traceable."""

    patient_token: str
    wound_id: str
    measurement_id: str
    captured_at: datetime
    anatomic_location: str
    wound_type: str

    # Objective measurements (this visit)
    volume_cm3: float
    surface_area_cm2: float
    max_depth_cm: float
    mean_depth_cm: float
    perimeter_cm: float
    quality_grade: str

    # Subjective wound bed characteristics — clinician-entered
    tissue_types: dict[str, float]   # {"granulation": 0.7, "slough": 0.2, "eschar": 0.1}
    drainage_amount: str             # "none" | "scant" | "moderate" | "heavy"
    drainage_quality: str            # "serous" | "serosanguineous" | "purulent" | "sanguineous"
    odor: str                        # "none" | "mild" | "foul"
    periwound_status: str
    pain_level_0_10: int

    # Optional extras
    progression: ProgressionDelta | None = None
    grafts_applied: list[GraftRecord] = field(default_factory=list)
    reimbursement: MedicareEstimate | None = None
    clinician_addendum: str = ""


def generate_progression_note(ctx: NoteContext) -> tuple[str, str, dict]:
    """Generate the note body. Returns (body_text, sha256_hex, metadata).

    The metadata dict captures the exact inputs hashed into the body so a
    future regeneration can prove the template + inputs produce the same
    text. Save it next to the note in the audit table.
    """
    lines: list[str] = []

    # ---- Header ----
    lines.append(f"WOUND CARE PROGRESS NOTE — {ctx.captured_at.strftime('%Y-%m-%d %H:%M %Z').rstrip()}")
    lines.append(f"Patient: {ctx.patient_token}")
    lines.append(f"Wound: {ctx.wound_id} | {ctx.anatomic_location} | {ctx.wound_type}")
    lines.append("")

    # ---- Objective findings ----
    lines.append("OBJECTIVE")
    lines.append(
        f"  Wound volume {ctx.volume_cm3:.2f} cm³, surface area {ctx.surface_area_cm2:.2f} cm², "
        f"max depth {ctx.max_depth_cm:.2f} cm, mean depth {ctx.mean_depth_cm:.2f} cm, "
        f"perimeter {ctx.perimeter_cm:.2f} cm. "
        f"Capture quality: grade {ctx.quality_grade}."
    )
    bed_pct = ", ".join(
        f"{int(v * 100)}% {tissue}"
        for tissue, v in sorted(ctx.tissue_types.items(), key=lambda kv: -kv[1])
        if v > 0
    )
    lines.append(f"  Wound bed: {bed_pct or 'not characterized'}.")
    lines.append(
        f"  Drainage: {ctx.drainage_amount} {ctx.drainage_quality}. "
        f"Odor: {ctx.odor}. Periwound: {ctx.periwound_status}. "
        f"Pain: {ctx.pain_level_0_10}/10."
    )
    lines.append("")

    # ---- Progression ----
    if ctx.progression:
        d = ctx.progression
        lines.append("PROGRESSION SINCE LAST VISIT")
        lines.append(f"  Interval: {d.days_since_prior} days.")
        if d.prior_area_cm2 is not None and d.area_change_cm2 is not None:
            arrow = "↓" if d.area_change_cm2 < 0 else "↑"
            lines.append(
                f"  Area: {d.prior_area_cm2:.2f} → {ctx.surface_area_cm2:.2f} cm² "
                f"({arrow} {abs(d.area_change_cm2):.2f} cm², {d.pct_area_change:+.1f}%)."
            )
        if d.prior_volume_cm3 is not None and d.volume_change_cm3 is not None:
            arrow = "↓" if d.volume_change_cm3 < 0 else "↑"
            lines.append(
                f"  Volume: {d.prior_volume_cm3:.2f} → {ctx.volume_cm3:.2f} cm³ "
                f"({arrow} {abs(d.volume_change_cm3):.2f} cm³, {d.pct_volume_change:+.1f}%)."
            )
        if d.prior_max_depth_cm is not None and d.depth_change_cm is not None:
            arrow = "↓" if d.depth_change_cm < 0 else "↑"
            lines.append(
                f"  Max depth: {d.prior_max_depth_cm:.2f} → {ctx.max_depth_cm:.2f} cm "
                f"({arrow} {abs(d.depth_change_cm):.2f} cm)."
            )
        if d.is_healing:
            lines.append("  Trajectory: HEALING — area reduction meets ≥10% threshold.")
        elif d.is_worsening:
            lines.append("  Trajectory: WORSENING — area increase ≥10% warrants reassessment.")
        else:
            lines.append("  Trajectory: STABLE — within ±10% area change.")
        lines.append("")

    # ---- Grafts ----
    if ctx.grafts_applied:
        lines.append("GRAFTS APPLIED THIS VISIT")
        for g in ctx.grafts_applied:
            lines.append(
                f"  • {g.product_name} | SN {g.serial_number} | Lot {g.lot_number} | "
                f"Exp {g.expiration_date.isoformat()} | "
                f"Applied area {g.applied_area_cm2:.1f} cm² of {g.package_size_cm2:.1f} cm² package."
            )
        lines.append("")

    # ---- Reimbursement (informational, not part of clinical record) ----
    if ctx.reimbursement:
        r = ctx.reimbursement
        lines.append("BILLING INFORMATION (estimate only — verify on remittance)")
        lines.append(
            f"  Primary CPT {r.primary_cpt} (${r.primary_cpt_payment:.2f}) "
            f"+ {r.additional_cpt_units} add-on unit(s) (${r.additional_units_payment:.2f}); "
            f"drug Q-code (${r.drug_payment:.2f}). "
            f"Estimated total allowed: ${r.total_payment:.2f}."
        )
        for note in r.notes:
            lines.append(f"  Note: {note}")
        lines.append("")

    # ---- Plan / Addendum ----
    if ctx.clinician_addendum.strip():
        lines.append("CLINICIAN ADDENDUM")
        lines.append("  " + ctx.clinician_addendum.strip().replace("\n", "\n  "))
        lines.append("")

    lines.append(f"Generated by WoundScan template {TEMPLATE_VERSION}.")
    body = "\n".join(lines).strip() + "\n"
    sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
    metadata = {
        "template_version": TEMPLATE_VERSION,
        "measurement_id": ctx.measurement_id,
        "wound_id": ctx.wound_id,
        "captured_at": ctx.captured_at.isoformat(),
        "tissue_types": ctx.tissue_types,
        "graft_count": len(ctx.grafts_applied),
        "reimbursement_total": (ctx.reimbursement.total_payment if ctx.reimbursement else None),
    }
    return body, sha, metadata
