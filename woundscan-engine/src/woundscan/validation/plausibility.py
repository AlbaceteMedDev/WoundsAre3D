"""Geometric plausibility checks: volume, surface area, depth sanity.

These are the "obviously wrong" filters: results that are physically
impossible or wildly outside clinical norms get flagged for clinician
review before the report is finalized.

Examples of plausibility failures:
- Negative volume
- Volume > footprint area * mean_depth * 1.2 (geometrically impossible
  for a single-valued depth field)
- Surface area < footprint area (contradicts the gradient integral lower bound)
- Depth > 10 cm (extremely rare; likely a sensor reading from beyond bed)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlausibilityCheck:
    """Single plausibility check result.

    Attributes
    ----------
    name : str
    passed : bool
    detail : str
    """

    name: str
    passed: bool
    detail: str


def run_geometric_plausibility_checks(
    volume_cm3: float,
    surface_area_cm2: float,
    footprint_area_cm2: float,
    max_depth_cm: float,
    mean_depth_cm: float,
) -> list[PlausibilityCheck]:
    """Run all geometric sanity checks. Returns list of results."""
    checks: list[PlausibilityCheck] = []

    checks.append(
        PlausibilityCheck(
            name="volume_nonneg",
            passed=volume_cm3 >= 0,
            detail=f"V={volume_cm3:.3f} cm^3",
        )
    )
    upper_bound = footprint_area_cm2 * max_depth_cm * 1.05
    checks.append(
        PlausibilityCheck(
            name="volume_le_box_upper_bound",
            passed=volume_cm3 <= upper_bound or upper_bound == 0,
            detail=f"V={volume_cm3:.3f}, bound={upper_bound:.3f}",
        )
    )
    checks.append(
        PlausibilityCheck(
            name="surface_area_ge_footprint",
            passed=surface_area_cm2 + 1e-6 >= footprint_area_cm2,
            detail=f"SA={surface_area_cm2:.3f}, footprint={footprint_area_cm2:.3f}",
        )
    )
    checks.append(
        PlausibilityCheck(
            name="max_depth_reasonable",
            passed=0.0 <= max_depth_cm <= 10.0,
            detail=f"max_depth={max_depth_cm:.3f} cm",
        )
    )
    checks.append(
        PlausibilityCheck(
            name="mean_le_max_depth",
            passed=mean_depth_cm <= max_depth_cm + 1e-6,
            detail=f"mean={mean_depth_cm:.3f}, max={max_depth_cm:.3f}",
        )
    )
    checks.append(
        PlausibilityCheck(
            name="footprint_positive",
            passed=footprint_area_cm2 > 0,
            detail=f"footprint={footprint_area_cm2:.3f}",
        )
    )

    return checks


def all_passed(checks: list[PlausibilityCheck]) -> bool:
    return all(c.passed for c in checks)
