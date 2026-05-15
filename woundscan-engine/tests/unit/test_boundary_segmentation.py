"""Tests for ml/boundary_segmentation.

Runs in a subprocess to dodge the coverage 7.x + numpy 1.26 + Py3.12
reload race (same root cause as the trajectory_plot and bundle_adjustment
tests). skimage's `rgb2hsv` and numpy reductions inside the fallback path
fail with `_NoValueType` under in-process coverage instrumentation.

Coverage on `boundary_segmentation.py` doesn't move from these tests
because the run happens in the child interpreter; the goal is behavioral
smoke for both the U-Net torch path and the fallback heuristic.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest


def _torch_importable() -> bool:
    try:
        import torch  # noqa: F401
        return True
    except ImportError:
        return False


_SUBPROCESS_RUNNER = r"""
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

from woundscan.ml.boundary_segmentation import (
    BoundarySegmentationModel,
    SegmentationResult,
    _UNet,
)

scenario = sys.argv[1]

# Build a synthetic 64x64 RGB image with a red-ish blob in the center.
img = np.full((64, 64, 3), 30, dtype=np.uint8)
img[20:44, 20:44, 0] = 200

def emit(result, model_version_expected=None):
    assert isinstance(result, SegmentationResult)
    out = {
        "binary_shape": list(result.binary_mask.shape),
        "binary_dtype": str(result.binary_mask.dtype),
        "conf_shape": list(result.confidence.shape),
        "conf_dtype": str(result.confidence.dtype),
        "conf_min": float(result.confidence.min()),
        "conf_max": float(result.confidence.max()),
        "model_version": result.model_version,
        "any_true": bool(result.binary_mask.any()),
    }
    sys.stdout.write(json.dumps(out))

if scenario == "fallback":
    result = BoundarySegmentationModel.fallback().segment(img)
    emit(result)
elif scenario == "fallback_grey":
    grey = np.full((32, 32, 3), 128, dtype=np.uint8)
    result = BoundarySegmentationModel.fallback().segment(grey)
    emit(result)
elif scenario == "missing_weights":
    with tempfile.TemporaryDirectory() as td:
        missing = Path(td) / "missing.pt"
        result = BoundarySegmentationModel(weights_path=missing).segment(img)
        emit(result)
elif scenario == "unet_random":
    unet = _UNet(n_classes=2)
    with tempfile.TemporaryDirectory() as td:
        ckpt = Path(td) / "random_unet.pt"
        unet.torch.save(unet.net.state_dict(), str(ckpt))
        result = BoundarySegmentationModel.from_weights(ckpt).segment(img)
        emit(result)
elif scenario == "corrupt_weights":
    with tempfile.TemporaryDirectory() as td:
        bad = Path(td) / "not_a_checkpoint.pt"
        bad.write_bytes(b"this is not a torch state_dict")
        result = BoundarySegmentationModel.from_weights(bad).segment(img)
        emit(result)
elif scenario == "idempotent_load":
    unet = _UNet(n_classes=2)
    with tempfile.TemporaryDirectory() as td:
        ckpt = Path(td) / "random_unet.pt"
        unet.torch.save(unet.net.state_dict(), str(ckpt))
        m = BoundarySegmentationModel.from_weights(ckpt)
        m.segment(img)
        m.segment(img)
        sys.stdout.write(json.dumps({"loaded": m._loaded}))
"""


def _run(scenario: str) -> dict:
    proc = subprocess.run(
        [sys.executable, "-c", _SUBPROCESS_RUNNER, scenario],
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr.decode(errors='replace')}"
    return json.loads(proc.stdout)


class TestFallbackPath:
    def test_red_blob_image_runs(self):
        out = _run("fallback")
        assert out["binary_shape"] == [64, 64]
        assert out["binary_dtype"] == "bool"
        assert out["conf_shape"] == [64, 64]
        assert out["conf_dtype"] == "float32"
        assert out["model_version"] == "fallback-heuristic-v0"

    def test_missing_weights_falls_back(self):
        out = _run("missing_weights")
        assert out["model_version"] == "fallback-heuristic-v0"
        assert out["binary_shape"] == [64, 64]

    def test_no_red_triggers_percentile_branch(self):
        # All-grey input → `score > 0.4` mask is empty → exercises the
        # `if not mask.any()` percentile-fallback branch. For a perfectly
        # uniform image the percentile threshold is also 0, so the result
        # is still empty — that's the documented behavior; we just need to
        # cover the branch without crashing.
        out = _run("fallback_grey")
        assert out["binary_shape"] == [32, 32]
        assert out["model_version"] == "fallback-heuristic-v0"


@pytest.mark.skipif(not _torch_importable(), reason="torch not installed")
class TestUNetPath:
    def test_loads_random_weights_and_runs_forward(self):
        out = _run("unet_random")
        assert out["binary_shape"] == [64, 64]
        assert out["binary_dtype"] == "bool"
        assert out["conf_shape"] == [64, 64]
        assert out["conf_dtype"] == "float32"
        # softmax probability must be in [0, 1].
        assert out["conf_min"] >= 0.0
        assert out["conf_max"] <= 1.0
        assert out["model_version"] == "random_unet"

    def test_corrupt_weights_falls_back_silently(self):
        out = _run("corrupt_weights")
        # Load throws → swallowed → fallback runs.
        assert out["binary_shape"] == [64, 64]
        # version derives from file stem (file exists, just isn't valid).
        assert out["model_version"] == "not_a_checkpoint"

    def test_ensure_loaded_is_idempotent(self):
        out = _run("idempotent_load")
        assert out["loaded"] is True
