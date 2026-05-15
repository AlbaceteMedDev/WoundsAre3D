"""Smoke test for output/trajectory_plot via subprocess isolation.

Coverage 7.x + matplotlib 3.10 + numpy 1.26 on Python 3.12 has a known
interaction: coverage's source-tree pre-instrumentation re-imports
modules that pull in numpy, and matplotlib's gridspec then hits a
`_NoValue` sentinel mismatch on multi-row `plt.subplots(..., sharex=True)`.

The function works correctly in production (no coverage tracer attached).
This test invokes the render path in a child interpreter so the test
asserts on real PNG bytes without touching the in-process coverage tracer.

The cost: trajectory_plot.py coverage isn't lifted by this test (it stays
at the same level as before). The production smoke is what matters for
the regulatory path — covered here. Coverage measurement of this module
is tracked as a follow-up in issue #2.
"""

from __future__ import annotations

import io
import subprocess
import sys

from PIL import Image


def _render_via_subprocess(
    n_points: int = 4,
    width_inches: float = 6.0,
    height_inches: float = 4.0,
    dpi: int = 120,
    mismatched: bool = False,
) -> subprocess.CompletedProcess[bytes]:
    """Invoke render_trajectory_png in a clean child interpreter.

    Returns the CompletedProcess so the caller can check stdout (PNG bytes)
    or stderr (ValueError for the negative case).
    """
    script = f"""
import sys
from datetime import datetime, timedelta, timezone
from woundscan.output.trajectory_plot import render_trajectory_png

n = {n_points}
mismatched = {mismatched}
ts = [datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=7 * i) for i in range(n)]
vol = [5.0 - 0.4 * i for i in range(n)]
sa = [12.0 - 1.0 * i for i in range(n)]
md = [0.8 - 0.1 * i for i in range(n)]
if mismatched:
    vol = vol[:-1]  # length mismatch on purpose
try:
    png = render_trajectory_png(
        timestamps=ts,
        volume_cm3=vol,
        surface_area_cm2=sa,
        max_depth_cm=md,
        width_inches={width_inches},
        height_inches={height_inches},
        dpi={dpi},
    )
    sys.stdout.buffer.write(png)
except ValueError as e:
    print(f"VALUE_ERROR: {{e}}", file=sys.stderr)
    sys.exit(2)
"""
    return subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        check=False,
    )


class TestRenderTrajectoryPng:
    def test_returns_png_magic_bytes(self):
        result = _render_via_subprocess()
        assert result.returncode == 0, f"stderr: {result.stderr.decode(errors='replace')}"
        assert result.stdout[:8] == b"\x89PNG\r\n\x1a\n"

    def test_dimensions_match_size_and_dpi(self):
        result = _render_via_subprocess(width_inches=4.0, height_inches=3.0, dpi=100)
        assert result.returncode == 0, f"stderr: {result.stderr.decode(errors='replace')}"
        img = Image.open(io.BytesIO(result.stdout))
        assert img.format == "PNG"
        assert abs(img.width - 400) <= 2
        assert abs(img.height - 300) <= 2

    def test_mismatched_input_lengths_raises(self):
        result = _render_via_subprocess(mismatched=True)
        assert result.returncode == 2
        assert b"VALUE_ERROR" in result.stderr

    def test_single_point_renders(self):
        result = _render_via_subprocess(n_points=1)
        assert result.returncode == 0, f"stderr: {result.stderr.decode(errors='replace')}"
        assert result.stdout[:8] == b"\x89PNG\r\n\x1a\n"
