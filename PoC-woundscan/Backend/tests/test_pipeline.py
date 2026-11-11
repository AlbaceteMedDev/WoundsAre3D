"""Offline tests for the wound-scan pipeline (no AWS needed).

    cd PoC-woundscan/Backend/tests && python -m pytest -q
"""

import json
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "lambdas", "step_functions", "shared"))

import local_run  # noqa: E402
import synthetic  # noqa: E402
from woundlib import imaging, narration  # noqa: E402


@pytest.mark.parametrize("preset", sorted(synthetic.PRESETS))
def test_synthetic_measurements_match_ground_truth(tmp_path, preset):
    L, W, D, dist, tilt, rot = synthetic.PRESETS[preset]
    bundle = tmp_path / "bundle"
    gt = synthetic.make_bundle(str(bundle), L, W, D, dist, tilt, rot)
    m = local_run.run(str(bundle), str(tmp_path / "out"), sam="fake", narrate="template")
    assert abs(m["length_mm"] - gt["length_mm"]) <= 1.0
    assert abs(m["width_mm"] - gt["width_mm"]) <= 1.0
    assert abs(m["depth_mm"] - gt["depth_mm"]) <= 0.5
    assert abs(m["bed_area_cm2"] - gt["bed_area_cm2"]) / gt["bed_area_cm2"] <= 0.05
    assert abs(m["peri_wound_area_cm2"] - gt["peri_wound_area_cm2"]) / gt["peri_wound_area_cm2"] <= 0.05
    out = tmp_path / "out" / "assets" / "processed" / "local-scan"
    for f in ("measurements.json", "diagram_top.svg", "diagram_cross.png", "narration.txt"):
        assert (out / f).stat().st_size > 0, f
    pre = json.loads((tmp_path / "out" / "state" / "work" / "local-scan" / "preprocess.json").read_text())
    assert pre["bestFrame"] == 4          # synthetic bundles make frame 4 the sharp one


def test_depth_grid_inference():
    for (w, h), (W, H) in [((256, 192), (1920, 1440)), ((256, 144), (3840, 2160))]:
        d, c = imaging.decode_depth(np.zeros(w * h, "<f4").tobytes(), np.zeros(w * h, np.uint8).tobytes(), W, H)
        assert d.shape == (h, w) and c.shape == (h, w)


def test_labelling_and_holes():
    m = np.zeros((20, 20), bool)
    m[2:8, 2:8] = True
    m[12:18, 12:18] = True
    m[4:6, 4:6] = False                      # a hole
    lab = imaging.label(m)
    assert lab.max() == 2
    filled = imaging.fill_holes(m)
    assert filled[4:6, 4:6].all()
    comp = imaging.component_at(m, 15, 15)
    assert comp[12:18, 12:18].all() and not comp[2:8, 2:8].any()


def test_narration_checks():
    m = {"length_mm": 42.3, "width_mm": 28.7, "bed_area_cm2": 9.84, "depth_mm": 6.2, "peri_wound_area_cm2": 31.42}
    assert narration.check(narration.template(m), m) == []
    bad = narration.template(m) + " This should heal well."
    assert any("clinical term" in p for p in narration.check(bad, m))
    assert any("missing value" in p for p in narration.check(narration.template({**m, "depth_mm": 7.0}), m))
    assert narration.clean("**Length** ‑ 42.3 mm") == "Length - 42.3 mm"
