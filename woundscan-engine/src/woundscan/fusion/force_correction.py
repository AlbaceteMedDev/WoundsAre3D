"""Probe compression correction.

When a clinician presses a probe into wound tissue, the tissue compresses
beneath the probe tip. The recorded depth therefore overestimates the
true bed depth by an amount that depends on:

- Tissue type at the contact point (granulation, slough, fibrous, etc.)
- Force category (light / medium / firm)

We apply a tabulated correction:

    d_true = d_measured - alpha(tissue) * f(force)

Coefficients are calibrated on silicone phantoms during development;
refined post-deployment from saline cross-checks.

The default table is conservative: errs on the side of *under-correcting*
so we never claim a wound is shallower than it is.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from woundscan.capture.probe import ForceCategory, ProbeMeasurement


@dataclass(frozen=True)
class ForceCorrectionTable:
    """Correction coefficients in mm per (tissue_type, force_category)."""

    coefficients_mm: dict[tuple[str, ForceCategory], float] = field(default_factory=dict)
    version: str = "v1.0.0"

    def get(self, tissue_type: str, force: ForceCategory, default_mm: float = 0.5) -> float:
        return self.coefficients_mm.get((tissue_type, force), default_mm)


def default_correction_table() -> ForceCorrectionTable:
    """Conservative defaults derived from internal phantom studies.

    Tissue types follow the standard wound classifier output:
    granulation, slough, eschar, fibrous, epithelial.

    Values are mm of compression at each force level.
    """
    return ForceCorrectionTable(
        coefficients_mm={
            ("granulation", ForceCategory.LIGHT): 0.3,
            ("granulation", ForceCategory.MEDIUM): 0.7,
            ("granulation", ForceCategory.FIRM): 1.2,
            ("slough", ForceCategory.LIGHT): 0.5,
            ("slough", ForceCategory.MEDIUM): 1.0,
            ("slough", ForceCategory.FIRM): 1.8,
            ("eschar", ForceCategory.LIGHT): 0.1,
            ("eschar", ForceCategory.MEDIUM): 0.2,
            ("eschar", ForceCategory.FIRM): 0.4,
            ("fibrous", ForceCategory.LIGHT): 0.2,
            ("fibrous", ForceCategory.MEDIUM): 0.4,
            ("fibrous", ForceCategory.FIRM): 0.8,
            ("epithelial", ForceCategory.LIGHT): 0.1,
            ("epithelial", ForceCategory.MEDIUM): 0.2,
            ("epithelial", ForceCategory.FIRM): 0.3,
            ("unknown", ForceCategory.LIGHT): 0.3,
            ("unknown", ForceCategory.MEDIUM): 0.6,
            ("unknown", ForceCategory.FIRM): 1.0,
        },
        version="v1.0.0",
    )


def apply_force_correction(
    measurement: ProbeMeasurement,
    tissue_type: str,
    table: ForceCorrectionTable | None = None,
) -> ProbeMeasurement:
    """Return a new ProbeMeasurement with the depth corrected and sigma inflated.

    The correction adds tissue-dependent variance to the per-point sigma
    to reflect the uncertainty in the correction coefficient itself
    (we don't know the EXACT compression at this exact point).
    """
    table = table or default_correction_table()
    correction_mm = table.get(tissue_type, measurement.force_category)
    corrected_depth = max(0.0, measurement.depth_mm - correction_mm)
    correction_uncertainty_mm = 0.5 * correction_mm
    new_sigma = float((measurement.sigma_mm**2 + correction_uncertainty_mm**2) ** 0.5)
    return ProbeMeasurement(
        x_mm=measurement.x_mm,
        y_mm=measurement.y_mm,
        depth_mm=corrected_depth,
        force_category=measurement.force_category,
        probe_type=measurement.probe_type,
        sigma_mm=new_sigma,
        auto_detected=measurement.auto_detected,
        notes=(measurement.notes + f" [force_corrected -{correction_mm:.2f}mm]").strip(),
    )
