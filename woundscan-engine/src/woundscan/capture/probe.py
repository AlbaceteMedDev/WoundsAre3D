"""Physical probe measurement ingestion.

The clinician probes the wound bed at 5-25 anchor points using a sterile
probe (cotton-tipped applicator, plastic gauge, Kundin gauge). For each
point they enter:

- The (x, y) in the wound photo (tap on photo or auto-detected probe tip)
- The depth measurement in mm
- A force category: light / medium / firm

Force category is required to apply the empirical compression correction
in `fusion/force_correction.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ForceCategory(StrEnum):
    """Categorical clinician force input. Mapped to mm-correction in fusion."""

    LIGHT = "light"
    MEDIUM = "medium"
    FIRM = "firm"


class ProbeType(StrEnum):
    """Type of probe used; affects systematic bias."""

    COTTON_TIP = "cotton_tip"
    PLASTIC_GAUGE = "plastic_gauge"
    KUNDIN_GAUGE = "kundin_gauge"
    OTHER = "other"


@dataclass(frozen=True)
class ProbeMeasurement:
    """A single probe-point measurement.

    Attributes
    ----------
    x_mm, y_mm : float
        Position in the wound-local mm coordinate frame.
    depth_mm : float
        Probe-measured depth at this point.
    force_category : ForceCategory
    probe_type : ProbeType
    sigma_mm : float
        Per-measurement standard deviation, before force correction. Set
        from the probe type and clinical assessment of measurement quality.
        Defaults to typical values per probe.
    auto_detected : bool
        True if probe tip was auto-detected by ML; False if manual tap.
    notes : str
    """

    x_mm: float
    y_mm: float
    depth_mm: float
    force_category: ForceCategory
    probe_type: ProbeType = ProbeType.COTTON_TIP
    sigma_mm: float = 0.5
    auto_detected: bool = False
    notes: str = ""

    def __post_init__(self) -> None:
        if self.depth_mm < 0:
            raise ValueError(f"depth_mm must be >= 0, got {self.depth_mm}")
        if self.sigma_mm <= 0:
            raise ValueError(f"sigma_mm must be > 0, got {self.sigma_mm}")


def default_sigma_mm(probe_type: ProbeType) -> float:
    """Typical per-measurement uncertainty per probe type, in mm.

    Calibrated values from internal phantom studies; refined post-deployment.
    """
    return {
        ProbeType.COTTON_TIP: 1.0,
        ProbeType.PLASTIC_GAUGE: 0.5,
        ProbeType.KUNDIN_GAUGE: 0.7,
        ProbeType.OTHER: 1.5,
    }[probe_type]
