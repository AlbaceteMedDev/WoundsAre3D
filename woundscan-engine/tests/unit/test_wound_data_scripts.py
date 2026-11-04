"""Offline tests for scripts/fetch_wound_segmentation_data.py and
scripts/evaluate_segmentation.py, on synthetic photographs and masks: the
scorer's metrics, mask normalisation, checksums, the layouts of the gated
datasets (which cannot be downloaded in CI), and the duplicate check."""

from __future__ import annotations

import csv
import hashlib
import http.client
import importlib.util
import json
import sys
import urllib.error
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


def test_mask_modes(tmp_path: Path) -> None:
    """Grey with alpha, a mask held only in alpha, and a palette whose index 0
    is white all read as the same 100-pixel wound."""
    wound = square(40, 40, (10, 10, 20, 20))
    Image.fromarray(np.stack([wound, np.full_like(wound, 255)], axis=2)).save(tmp_path / "la.png")
    only_alpha = np.zeros((40, 40, 4), np.uint8)
    only_alpha[..., 3] = wound
    Image.fromarray(only_alpha).save(tmp_path / "alpha.png")
    palette = Image.fromarray((wound > 0).astype(np.uint8) * 2)
    palette.putpalette([255, 255, 255, 0, 0, 0, 255, 0, 0])
    palette.save(tmp_path / "palette.png")
    for name in ("la", "alpha", "palette"):
        assert evaluate.read_mask(tmp_path / f"{name}.png").sum() == 100, name
        assert fetch.binary(tmp_path / f"{name}.png").sum() == 100, name


def test_checksums_and_paths(tmp_path: Path) -> None:
    assert fetch.check(b"hello\n", {"git_sha1": "ce013625030ba8dba906f756967f9e9ca394464a"})
    assert fetch.check(
        b"",
        {"sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "size": 0},
    )
    assert not fetch.check(b"x", {"sha256": "0" * 64})
    with pytest.raises(RuntimeError, match="leaves"):
        fetch.inside(tmp_path, "../escape.png")
    assert fetch.outside_git(tmp_path / "data") == (tmp_path / "data").resolve()
    for refuse in (fetch.outside_git, evaluate.outside_git):  # this checkout is a git work tree
        with pytest.raises(SystemExit, match="git work tree"):
            refuse(SCRIPTS / "data")


def test_get_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    """A body cut short and a rate limit are tried again; a refusal is not."""
    calls = []

    class Reply:
        headers: dict[str, str] = {}

        def __enter__(self) -> Reply:
            return self

        def __exit__(self, *exc: object) -> None:
            return None

        def read(self) -> bytes:
            return b"ok"

    def flaky(req, timeout):  # type: ignore[no-untyped-def]
        calls.append(req.full_url)
        if len(calls) == 1:
            raise http.client.IncompleteRead(b"o", 1)
        if len(calls) == 2:
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many", {"Retry-After": "3"}, None)
        return Reply()

    def refuse(req, timeout):  # type: ignore[no-untyped-def]
        calls.append(req.full_url)
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr(fetch.time, "sleep", lambda s: None)
    monkeypatch.setattr(fetch.urllib.request, "urlopen", flaky)
    assert fetch.get("https://example.org/a")[0] == b"ok" and len(calls) == 3
    calls.clear()
    monkeypatch.setattr(fetch.urllib.request, "urlopen", refuse)
    with pytest.raises(urllib.error.HTTPError):
        fetch.get("https://example.org/b")
    assert len(calls) == 1


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
    nested = raw / "woundseg-nested"  # the same file name in two folders: refused, not dropped
    for kind in ("foot", "leg"):
        save(scene(4, 32, 32), nested / "unpacked" / kind / "sample" / "1.png")
        save(square(32, 32, (2, 2, 9, 9)), nested / "unpacked" / kind / "mask" / "1.png")
    with pytest.raises(RuntimeError, match="one to one"):
        fetch.woundseg(tmp_path / "out", nested)

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
    # A later fetch's byte-for-byte copy of two/turned names the first copy,
    # one/padded, with two/turned's turns: never a copy of a copy.
    later = [{**rows[2], "key": "three/0", "dataset": "three", "duplicate_of": ""}]
    del later[0]["duplicate_turns"]
    earlier = [{**r, "duplicate_turns": str(r.get("duplicate_turns", ""))} for r in rows]
    fetch.mark_repeats(later, earlier)
    assert (later[0]["duplicate_of"], later[0]["duplicate_turns"]) == ("one/padded", 2)


def fake_dataset(name: str, seed: int) -> dict[str, object]:
    """A two-photograph stand-in for a DATASETS entry, made without a download."""

    def layout(out: Path, raw: Path) -> list[dict[str, object]]:
        rows = []
        for i in range(2):
            image = save(scene(seed + i, 32, 24), raw / f"{i}.png")
            mask = save(square(32, 24, (4, 4, 12, 12)), raw / f"{i}_mask.png")
            rows.append(fetch.pair(out, name, str(i), image, mask))
        return rows

    return {
        "fetch": lambda raw: None,
        "layout": layout,
        "group": "confirm-first" if name == "two" else "usable",
        "licence": "CC BY 4.0",
        "licence_url": "https://creativecommons.org/licenses/by/4.0/",
        "source": "test",
        "contents": "test",
        "attribution": "test",
    }


def test_build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Datasets are laid out in DATASETS order whatever the command line says;
    a re-run that leaves out a dataset already in the folder is refused; and
    LICENSES.md says what each group allows and that the masks were redrawn."""
    sets = {"one": fake_dataset("one", 0), "two": fake_dataset("two", 0)}  # the same photographs
    monkeypatch.setattr(fetch, "DATASETS", sets)
    rows = fetch.build(["two", "one"], tmp_path, [])
    assert [r["key"] for r in rows] == ["one/0", "one/1", "two/0", "two/1"]
    assert [r["duplicate_of"] for r in rows] == ["", "", "one/0", "one/1"]
    assert {r["mask_target"] for r in rows} == {"wound"}
    licences = (tmp_path / "LICENSES.md").read_text()
    assert "Use: company use allowed" in licences
    assert "Use: internal testing allowed" in licences and "binarised" in licences
    with pytest.raises(SystemExit, match="also holds two"):
        fetch.build(["one"], tmp_path, [])
    assert len(fetch.read_manifest(tmp_path)) == 4  # left as it was


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


def test_selection_follows_repeats() -> None:
    """Each photograph is scored once, from the first selected dataset that
    lists it, even when the copy it repeats is not selected or not here."""
    every = [
        {"key": "a/1", "dataset": "a", "duplicate_of": ""},
        {"key": "a/2", "dataset": "a", "duplicate_of": ""},
        {"key": "b/1", "dataset": "b", "duplicate_of": "a/1"},
        {"key": "b/2", "dataset": "b", "duplicate_of": ""},
        {"key": "c/1", "dataset": "c", "duplicate_of": "b/1"},  # a chain
        {"key": "c/2", "dataset": "c", "duplicate_of": "x/9"},  # first copy in another manifest
        {"key": "c/3", "dataset": "c", "duplicate_of": "x/9"},
    ]

    def keys(datasets: list[str] | None, every_copy: bool = False) -> list[str]:
        return [r["key"] for r in evaluate.select(every, datasets, every_copy)]

    assert keys(None) == ["a/1", "a/2", "b/2", "c/2"]
    assert keys(["b"]) == ["b/1", "b/2"]
    assert keys(["b", "c"]) == ["b/1", "b/2", "c/2"]
    assert keys(["c"]) == ["c/1", "c/2"]
    assert len(keys(None, every_copy=True)) == 7


def test_evaluate_report_and_groups(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The report lands under DATA by default and never in a git work tree; a
    healed photograph alone in its band is reported, not a crash; peri-wound
    masks are kept out of the pooled rows; and weights that do not load stop
    the run before anything is written."""
    data, pred = tmp_path / "data", tmp_path / "pred"
    truths = {
        "set/0": square(40, 40, (10, 10, 30, 30)),
        "set/1": np.zeros((40, 40), np.uint8),  # healed: nothing to find
        "peri/0": square(40, 40, (5, 5, 35, 35)),
    }
    rows = []
    for key, truth in truths.items():
        name, i = key.split("/")
        save(scene(len(rows), 40, 40), data / "images" / name / f"{i}.png")
        save(truth, data / "masks" / name / f"{i}.png")
        save(truth, pred / name / f"{i}.png")
        rows.append(
            {
                "key": key,
                "dataset": name,
                "id": i,
                "image": f"images/{name}/{i}.png",
                "mask": f"masks/{name}/{i}.png",
                "mask_target": "wound and peri-wound skin" if name == "peri" else "wound",
                "duplicate_of": "",
            }
        )
    with open(data / "manifest.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    def run(*args: str) -> int:
        monkeypatch.setattr(sys, "argv", ["evaluate", "--data", str(data), *args])
        return evaluate.main()

    assert run("--pred", str(pred)) == 0
    summary = json.loads((data / "reports" / "pred" / "summary.json").read_text())
    assert summary["groups"]["all"]["n"] == 2 and summary["groups"]["dataset peri"]["n"] == 1
    assert summary["groups"]["wound under 1 % of frame"]["recall"] == {"n": 0}
    assert summary["scored_apart"] == ["peri (wound and peri-wound skin)"]
    with pytest.raises(SystemExit, match="git work tree"):
        run("--pred", str(pred), "--report", str(SCRIPTS / "report"))
    assert not (SCRIPTS / "report").exists()
    bad = tmp_path / "boundary_v9.pt"
    bad.write_bytes(b"not a state dict")
    with pytest.raises(SystemExit):
        run("--engine", "--weights", str(bad), "--report", str(tmp_path / "engine"))
    assert not (tmp_path / "engine").exists()
