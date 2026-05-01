"""CSV export of measurements (no PHI; uses opaque tokens).

Writes a flat CSV row per measurement. Columns are stable; new columns
appended at the end so consumers can rely on column names but not
positions.
"""
from __future__ import annotations

import csv
import io
from typing import Iterable, Sequence


COLUMNS = (
    "measurement_id",
    "patient_token",
    "wound_id",
    "captured_at",
    "clinician_id",
    "engine_version",
    "volume_cm3",
    "volume_ci_low",
    "volume_ci_high",
    "surface_area_cm2",
    "surface_area_ci_low",
    "surface_area_ci_high",
    "max_depth_cm",
    "mean_depth_cm",
    "perimeter_cm",
    "footprint_area_cm2",
    "quality_grade",
    "quality_score",
    "n_probe_anchors",
    "fiducial_count",
    "model_boundary_version",
    "model_tissue_version",
)


def write_measurement_csv(rows: Iterable[dict[str, object]], columns: Sequence[str] = COLUMNS) -> str:
    """Serialize rows to CSV string. Missing columns are blanked."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(columns), extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()
