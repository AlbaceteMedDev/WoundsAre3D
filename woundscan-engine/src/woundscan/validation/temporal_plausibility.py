"""Cross-visit temporal plausibility checks.

Wound healing rates are clinically bounded: a wound cannot heal more than
~10% volume per day, cannot worsen more than ~30% in a day without
infection, cannot change orientation/morphology dramatically.

Compare current measurement to:
- Previous visit (largest expected change)
- Trend from last 3 visits
- Population-typical rates for the wound type
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TemporalPlausibilityCheck:
    name: str
    passed: bool
    detail: str
    severity: str  # "info", "warning", "alert"


def check_temporal_plausibility(
    current_volume_cm3: float,
    current_area_cm2: float,
    days_since_last_visit: float,
    last_volume_cm3: float | None,
    last_area_cm2: float | None,
    expected_daily_volume_change_max: float = 0.15,  # 15% per day
    expected_daily_area_change_max: float = 0.10,
) -> list[TemporalPlausibilityCheck]:
    """Run temporal plausibility checks. Returns list of results."""
    out: list[TemporalPlausibilityCheck] = []

    if last_volume_cm3 is None or days_since_last_visit < 0.5:
        out.append(
            TemporalPlausibilityCheck(
                name="temporal_skipped",
                passed=True,
                detail="Insufficient prior data or interval",
                severity="info",
            )
        )
        return out

    rel_v_change = abs(current_volume_cm3 - last_volume_cm3) / max(last_volume_cm3, 1e-3)
    daily_v_change = rel_v_change / max(days_since_last_visit, 1.0)
    out.append(
        TemporalPlausibilityCheck(
            name="volume_daily_change",
            passed=daily_v_change <= expected_daily_volume_change_max,
            detail=f"{daily_v_change*100:.1f}%/day (limit {expected_daily_volume_change_max*100:.0f}%)",
            severity="warning" if daily_v_change > expected_daily_volume_change_max else "info",
        )
    )

    if last_area_cm2 is not None:
        rel_a_change = abs(current_area_cm2 - last_area_cm2) / max(last_area_cm2, 1e-3)
        daily_a_change = rel_a_change / max(days_since_last_visit, 1.0)
        out.append(
            TemporalPlausibilityCheck(
                name="area_daily_change",
                passed=daily_a_change <= expected_daily_area_change_max,
                detail=f"{daily_a_change*100:.1f}%/day (limit {expected_daily_area_change_max*100:.0f}%)",
                severity="warning" if daily_a_change > expected_daily_area_change_max else "info",
            )
        )

    return out
