"""Phantom calibration tracking.

Each clinician scans a known silicone phantom monthly. Results feed into
a longitudinal accuracy database. We compute drift over time and alert
when measured error exceeds the validated tolerance budget.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class PhantomScan:
    """A single phantom scan record.

    Attributes
    ----------
    phantom_id : str
        Internal phantom catalog ID.
    clinician_id : str
    timestamp : datetime
    measured_volume_cm3 : float
    measured_surface_area_cm2 : float
    true_volume_cm3 : float
    true_surface_area_cm2 : float
    """

    phantom_id: str
    clinician_id: str
    timestamp: datetime
    measured_volume_cm3: float
    measured_surface_area_cm2: float
    true_volume_cm3: float
    true_surface_area_cm2: float

    @property
    def volume_error_pct(self) -> float:
        return abs(self.measured_volume_cm3 - self.true_volume_cm3) / max(
            abs(self.true_volume_cm3), 1e-9
        ) * 100.0

    @property
    def surface_area_error_pct(self) -> float:
        return abs(self.measured_surface_area_cm2 - self.true_surface_area_cm2) / max(
            abs(self.true_surface_area_cm2), 1e-9
        ) * 100.0


@dataclass
class PhantomCalibration:
    """Aggregated calibration state for a clinician.

    Attributes
    ----------
    clinician_id : str
    scans : list[PhantomScan]
    drift_alert_threshold_pct : float
    """

    clinician_id: str
    scans: list[PhantomScan] = field(default_factory=list)
    drift_alert_threshold_pct: float = 3.0

    def latest(self) -> PhantomScan | None:
        return self.scans[-1] if self.scans else None

    def in_drift_alert(self) -> bool:
        latest = self.latest()
        if latest is None:
            return False
        return latest.volume_error_pct > self.drift_alert_threshold_pct

    def recent_volume_error_pct(self, n: int = 3) -> float | None:
        if len(self.scans) < n:
            return None
        recent = self.scans[-n:]
        return sum(s.volume_error_pct for s in recent) / n


def record_phantom_scan(
    calibration: PhantomCalibration, scan: PhantomScan
) -> PhantomCalibration:
    """Append a scan to a calibration record."""
    calibration.scans.append(scan)
    return calibration
