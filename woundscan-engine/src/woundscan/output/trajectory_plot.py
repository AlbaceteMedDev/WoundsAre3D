"""Render trajectory PNG: volume / surface area / depth over time.

Used in the web dashboard wound detail page and in the PDF report when
prior measurements exist.
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from datetime import datetime


def render_trajectory_png(
    timestamps: Sequence[datetime],
    volume_cm3: Sequence[float],
    surface_area_cm2: Sequence[float],
    max_depth_cm: Sequence[float],
    *,
    width_inches: float = 6.0,
    height_inches: float = 4.0,
    dpi: int = 120,
) -> bytes:
    """Render a 3-panel trajectory plot. Returns PNG bytes."""
    if len({len(timestamps), len(volume_cm3), len(surface_area_cm2), len(max_depth_cm)}) != 1:
        raise ValueError("All input arrays must have the same length")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 1, figsize=(width_inches, height_inches), sharex=True, dpi=dpi)
    axes[0].plot(timestamps, volume_cm3, marker="o")
    axes[0].set_ylabel("V (cm³)")
    axes[0].set_title("Wound Trajectory")
    axes[1].plot(timestamps, surface_area_cm2, marker="o", color="C1")
    axes[1].set_ylabel("SA (cm²)")
    axes[2].plot(timestamps, max_depth_cm, marker="o", color="C2")
    axes[2].set_ylabel("Max Depth (cm)")
    axes[2].set_xlabel("Visit")
    axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate()
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()
