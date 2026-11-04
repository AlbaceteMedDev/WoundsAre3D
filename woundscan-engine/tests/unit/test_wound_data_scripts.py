"""Offline tests for scripts/fetch_wound_segmentation_data.py and
scripts/evaluate_segmentation.py, on synthetic photographs and masks: the
scorer's metrics, mask normalisation, checksums, the layouts of the gated
datasets (which cannot be downloaded in CI), and the duplicate check."""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
import zipfile
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest
from PIL import Image

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fetch = load("fetch_wound_segmentation_data")
evaluate = load("evaluate_segmentation")


def scene(seed: int, w: int, h: int) -> np.ndarray:
    """A smooth random RGB scene, so thumbnails of it stay recognisable."""
    rng = np.random.default_rng(seed)
    small = rng.integers(0, 255, (6, 6, 3), dtype=np.uint8)
    return np.asarray(Image.fromarray(small).resize((w, h), Image.BICUBIC))


def save(a: np.ndarray, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(a).save(path)
    return path


def square(w: int, h: int, box: tuple[int, int, int, int], value: int = 255) -> np.ndarray:
    a = np.zeros((h, w), np.uint8)
    x0, y0, x1, y1 = box
    a[y0:y1, x0:x1] = value
    return a


def test_score_known_overlap() -> None:
    truth = square(40, 40, (10, 10, 20, 20)) > 0
    shifted = square(40, 40, (15, 10, 25, 20)) > 0
    s = evaluate.score(shifted, truth)
    assert s["dice"] == pytest.approx(0.5)
    assert s["iou"] == pytest.approx(50 / 150)
    assert s["precision"] == pytest.approx(0.5) and s["recall"] == pytest.approx(0.5)
    assert s["area_error"] == pytest.approx(0.0)
    assert 0.0 < s["boundary_f1"] < 1.0
    same = evaluate.score(truth, truth)
    assert same["dice"] == same["boundary_f1"] == 1.0
    empty = np.zeros_like(truth)
    assert evaluate.score(empty, empty)["dice"] == 1.0
    missed = evaluate.score(empty, truth)
    assert missed["dice"] == 0.0 and missed["recall"] == 0.0 and missed["boundary_f1"] == 0.0


def test_binary_masks(tmp_path: Path) -> None:
    soft = square(50, 50, (10, 10, 30, 30))  # rows and columns 10-29 are wound
    soft[30, 10:20] = 200  # a resampled edge: over half scale outside, so wound
    soft[29, 10:20] = 60  # and under half scale inside, so background
    m = fetch.binary(save(soft, tmp_path / "soft.png"))
    assert m.dtype == bool and m[30, 10:20].all() and not m[29, 10:20].any() and m.sum() == 400
    ones = fetch.binary(save(square(50, 50, (0, 0, 5, 5), value=1), tmp_path / "ones.png"))
    assert ones.sum() == 25
    with pytest.raises(RuntimeError, match="mid-grey"):
        fetch.binary(save(scene(1, 50, 50), tmp_path / "photo.png"))


def test_checksums_and_paths(tmp_path: Path) -> None:
    assert fetch.check(b"hello\n", {"git_sha1": "ce013625030ba8dba906f756967f9e9ca394464a"})
    assert fetch.check(
        b"",
        {"sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "size": 0},
    )
    assert not fetch.check(b"x", {"sha256": "0" * 64})
    with pytest.raises(RuntimeError, match="leaves"):
        fetch.inside(tmp_path, "../escape.png")


def test_gated_layouts(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    for split, names in (("train", ["0011", "0012"]), ("validation", ["0001"])):
        for i, n in enumerate(names):
            save(scene(i, 64, 48), raw / "fuseg" / split / "images" / f"{n}.png")
            save(square(64, 48, (5, 5, 20, 20)), raw / "fuseg" / split / "labels" / f"{n}.png")
    save(scene(9, 64, 48), raw / "fuseg" / "test" / "images" / "1011.png")  # no mask: left out
    rows = fetch.fuseg(tmp_path / "out", raw / "fuseg")
    assert [(r["id"], r["split"]) for r in rows] == [
        ("0011", "train"),
        ("0012", "train"),
        ("0001", "validation"),
    ]

    (raw / "woundseg").mkdir()
    with zipfile.ZipFile(raw / "woundseg" / "wseg_dataset.zip", "w") as z:
        for n in ("a", "b"):
            for folder, a in (
                ("sample", scene(3, 32, 32)),
                ("mask", square(32, 32, (2, 2, 9, 9), 1)),
            ):
                p = save(a, tmp_path / "zipsrc" / folder / f"{n}.png")
                z.write(p, f"wseg/{folder}/{n}.png")
    rows = fetch.woundseg(tmp_path / "out", raw / "woundseg")
    assert [r["id"] for r in rows] == ["a", "b"]
    assert np.unique(np.asarray(Image.open(tmp_path / "out" / rows[0]["mask"]))).tolist() == [
        0,
        255,
    ]

    v2 = raw / "co2wounds-v2"
    for stem, ext, split in (("IMG435", ".jpg", "train"), ("IMG864", ".png", "val")):
        save(scene(5, 40, 30), v2 / "imgs" / f"{stem}{ext}")
        save(square(40, 30, (3, 3, 10, 10)), v2 / "masks" / f"{stem}.png")
        save(scene(5, 40, 30), v2 / "split" / split / f"{stem}{ext}")
    save(scene(6, 40, 30), v2 / "imgs" / "IMG999.jpg")  # a test photograph: no mask
    (v2 / "split" / "test").mkdir()
    rows = fetch.co2wounds_v2(tmp_path / "out", v2)
    assert [(r["id"], r["split"], Path(r["image"]).suffix) for r in rows] == [
        ("IMG435", "train", ".jpg"),
        ("IMG864", "val", ".png"),
    ]


def test_repeats(tmp_path: Path) -> None:
    """A photograph padded to a square in one dataset, and turned half round at
    another size in a second, is one photograph; an unrelated one is not."""
    base = scene(7, 60, 90)
    padded = np.zeros((90, 90, 3), np.uint8)
    padded[:, 15:75] = base
    rows = []
    for key, a in (
        ("one/padded", padded),
        ("one/copy", padded),
        ("two/turned", np.asarray(Image.fromarray(base).resize((120, 180)))[::-1, ::-1]),
        ("two/other", scene(8, 60, 90)),
    ):
        p = save(np.ascontiguousarray(a), tmp_path / f"{key}.png")
        rows.append(
            {
                "key": key,
                "dataset": key.split("/")[0],
                "path": p,
                "duplicate_of": "",
                "image_sha256": fetch.hashlib.sha256(p.read_bytes()).hexdigest(),
            }
        )
    fetch.mark_repeats(rows, [])
    found = {r["key"]: (r["duplicate_of"], r.get("duplicate_turns")) for r in rows}
    assert found == {
        "one/padded": ("", None),
        "one/copy": ("one/padded", 0),
        "two/turned": ("one/padded", 2),
        "two/other": ("", None),
    }


def test_evaluate_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data, pred = tmp_path / "data", tmp_path / "pred"
    truth = square(40, 40, (10, 10, 20, 20))
    rows = []
    for i, guess in enumerate([truth, square(40, 40, (15, 10, 25, 20))]):
        save(scene(i, 40, 40), data / "images" / "set" / f"{i}.png")
        save(truth, data / "masks" / "set" / f"{i}.png")
        save(guess, pred / "set" / f"{i}.png")
        rows.append(
            {
                "key": f"set/{i}",
                "dataset": "set",
                "id": str(i),
                "image": f"images/set/{i}.png",
                "mask": f"masks/set/{i}.png",
                "duplicate_of": "",
            }
        )
    with open(data / "manifest.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    report = tmp_path / "report"
    monkeypatch.setattr(
        sys, "argv", ["evaluate", "--data", str(data), "--pred", str(pred), "--report", str(report)]
    )
    assert evaluate.main() == 0
    summary = json.loads((report / "summary.json").read_text())
    assert summary["photographs"] == 2
    assert summary["groups"]["all"]["dice"]["median"] == pytest.approx(0.75)
    assert summary["groups"]["all"]["dice_under_0.5"] == 0.0
