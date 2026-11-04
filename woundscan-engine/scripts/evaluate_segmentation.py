"""Score wound segmentation on the real-wound test set that
fetch_wound_segmentation_data.py lays out.

    python scripts/evaluate_segmentation.py --data DIR --pred PRED
    python scripts/evaluate_segmentation.py --data DIR --engine [--weights boundary_v1.pt]

PRED holds one mask per photograph, PRED/<dataset>/<id>.png, at the
photograph's size and non-zero where the model sees wound (a palette image is
read by its indices). --engine runs the engine's BoundarySegmentationModel
instead, keeping its masks in REPORT/pred/; given --weights, it stops unless
the U-Net really loads, and segments photographs larger than --max-side at that
size, scaling each mask back. The report goes to --report, by default
DIR/reports/<run>; it holds masks made from patient photographs, so it is
refused inside a git work tree. Each photograph is scored once, from the first
selected dataset that lists it (--all scores every copy).

Per photograph: Dice, IoU, precision, recall, boundary F1 (boundary pixels
within 0.75 % of the image diagonal of the other boundary) and the signed
error in wound area. Printed per dataset and by the wound's share of the
frame, as medians and quartiles with the share of photographs under Dice 0.5,
and written to REPORT/scores.csv and REPORT/summary.json. A dataset whose masks
take in more than the wound (WoundSeg's include the peri-wound skin) is scored
in its own row only, not pooled with the rest. Where LUTSeg's five-clinician
subset is present, the clinicians' agreement with one another is printed too:
about as well as a model can be expected to do.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import itertools
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from scipy import ndimage

ENGINE = Path(__file__).resolve().parents[1]
BANDS = [
    (0.0, 0.01, "under 1 % of frame"),
    (0.01, 0.05, "1-5 % of frame"),
    (0.05, 1.01, "over 5 % of frame"),
]
METRICS = ["dice", "iou", "precision", "recall", "boundary_f1", "area_error"]
NAN = float("nan")


def outside_git(path: Path) -> Path:
    """path resolved, stopping the run if it lies inside a git work tree (this
    repository's or any other), where masks of patient photographs could be
    committed."""
    p = path.expanduser().resolve()
    for d in (p, *p.parents):
        if (d / ".git").exists():
            sys.exit(f"{p} is inside the git work tree at {d}: keep the report out of it")
    return p


def plane(im: Image.Image) -> np.ndarray:
    """A mask image as one 2-D array: a palette image's indices; otherwise its
    brightest colour channel, transparent pixels counting as background - or
    the alpha channel itself, where that is all the image holds."""
    a = np.asarray(im)
    if a.ndim == 2:
        return a
    if im.mode in ("LA", "La", "PA", "RGBA", "RGBa"):
        colour, alpha = a[..., :-1].max(axis=2), a[..., -1]
        return np.where(alpha > 0, colour, 0) if colour.any() else alpha
    return a.max(axis=2)


def read_mask(path: Path) -> np.ndarray:
    return plane(Image.open(path)) > 0


def edge(m: np.ndarray) -> np.ndarray:
    return m & ~ndimage.binary_erosion(m, border_value=0)


def score(pred: np.ndarray, truth: np.ndarray) -> dict[str, float]:
    """Overlap, boundary and area agreement of a predicted mask with the truth."""
    inter, p, t = float((pred & truth).sum()), float(pred.sum()), float(truth.sum())
    out = {
        "dice": 2 * inter / (p + t) if p + t else 1.0,
        "iou": inter / (p + t - inter) if p + t else 1.0,
        "precision": inter / p if p else NAN,
        "recall": inter / t if t else NAN,
        "area_error": (p - t) / t if t else NAN,
    }
    tol = 0.0075 * float(np.hypot(*truth.shape))
    ys, xs = np.nonzero(pred | truth)
    if len(ys):  # only the region round the two outlines matters
        m = int(tol) + 2
        win = (
            slice(max(ys.min() - m, 0), ys.max() + m + 1),
            slice(max(xs.min() - m, 0), xs.max() + m + 1),
        )
        pred, truth = pred[win], truth[win]
    bp, bt = edge(pred), edge(truth)
    if bp.any() and bt.any():
        near_t = ndimage.distance_transform_edt(~bt)[bp] <= tol
        near_p = ndimage.distance_transform_edt(~bp)[bt] <= tol
        bprec, brec = float(near_t.mean()), float(near_p.mean())
        out["boundary_f1"] = 2 * bprec * brec / (bprec + brec) if bprec + brec else 0.0
    else:
        out["boundary_f1"] = float(bp.any() == bt.any())
    return out


def select(
    every: list[dict[str, str]], datasets: list[str] | None, every_copy: bool
) -> list[dict[str, str]]:
    """The rows of the named datasets, once per photograph unless every_copy:
    of the copies selected, the first one listed. duplicate_of is followed to
    the copy the others repeat, even through a chain or into another folder's
    manifest, so a copy whose first is not selected is still scored."""
    link = {r["key"]: r["duplicate_of"] for r in every}

    def first(key: str) -> str:
        seen = set()
        while link.get(key) and key not in seen:
            seen.add(key)
            key = link[key]
        return key

    rows, taken = [], set()
    for r in every:
        if datasets and r["dataset"] not in datasets:
            continue
        photo = first(r["key"])
        if every_copy or photo not in taken:
            taken.add(photo)
            rows.append(r)
    return rows


def load_engine(weights: Path | None) -> Any:
    """The engine's segmentation model; with weights, only if its U-Net loads."""
    sys.path.insert(0, str(ENGINE / "src"))
    from woundscan.ml.boundary_segmentation import BoundarySegmentationModel

    if weights is None:
        return BoundarySegmentationModel.fallback()
    if not weights.is_file():
        sys.exit(f"--weights {weights}: no such file")
    model = BoundarySegmentationModel.from_weights(weights)
    model._ensure_loaded()  # the engine falls back to its colour heuristic without saying so
    if model._unet is None or model._unet.net is None:
        if importlib.util.find_spec("torch") is None:
            sys.exit("--weights needs torch, which is not installed: pip install -e '.[ml]'")
        sys.exit(
            f"--weights {weights}: torch could not load it as a state dict for the engine's "
            "U-Net (a trainer checkpoint such as {'state_dict': ...}, or a whole pickled model, "
            "will not do); the engine would have used its colour heuristic instead"
        )
    return model


def run_engine(
    model: Any, rows: list[dict[str, str]], data: Path, dest: Path, max_side: int
) -> None:
    """Segment every photograph; masks go to dest, at each photograph's size."""
    for i, r in enumerate(rows, 1):
        im = Image.open(data / r["image"]).convert("RGB")
        scale = max_side / max(im.size) if max_side and max(im.size) > max_side else 1.0
        small = (
            im.resize(
                (max(1, round(im.width * scale)), max(1, round(im.height * scale))),
                Image.BILINEAR,
            )
            if scale < 1
            else im
        )
        mask = model.segment(np.asarray(small)).binary_mask
        found = Image.fromarray(np.where(mask, 255, 0).astype(np.uint8))
        if scale < 1:
            found = found.resize(im.size, Image.NEAREST)
        out = dest / r["dataset"] / f"{r['id']}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        found.save(out)
        if i % 25 == 0 or i == len(rows):
            print(f"  segmented {i}/{len(rows)}", flush=True)


def clinicians(data: Path) -> list[float]:
    """Pairwise Dice of the five clinicians' wound masks on LUTSeg's gold subset."""
    root = data / "raw" / "lutseg"
    if not (root / "gold_standard" / "manifest.jsonl").exists():
        return []
    pairs = []
    for line in (root / "gold_standard" / "manifest.jsonl").read_text().splitlines():
        entry = json.loads(line)
        masks = [read_mask(root / v) for k, v in sorted(entry.items()) if k.endswith("_wound_mask")]
        pairs += [
            2 * float((a & b).sum()) / max(float(a.sum() + b.sum()), 1.0)
            for a, b in itertools.combinations(masks, 2)
        ]
    return pairs


def spread(values: list[float]) -> dict[str, float]:
    v = np.array([x for x in values if not np.isnan(x)])
    if not len(v):
        return {"n": 0}
    q1, med, q3 = np.percentile(v, [25, 50, 75])
    return {
        "n": int(len(v)),
        "median": float(med),
        "q1": float(q1),
        "q3": float(q3),
        "mean": float(v.mean()),
    }


def summarise(group: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {m: spread([g[m] for g in group]) for m in METRICS}
    out["n"] = len(group)
    out["dice_under_0.5"] = float(np.mean([g["dice"] < 0.5 for g in group])) if group else 0.0
    return out


def line(name: str, s: dict[str, Any]) -> str:
    def m(metric: str, stat: str = "median") -> float:
        return float(s[metric].get(stat, NAN))  # undefined where no truth mask has a wound

    return (
        f"{name:28s} {s['n']:4d}  {m('dice'):5.3f} [{m('dice', 'q1'):5.3f}-{m('dice', 'q3'):5.3f}]"
        f"  {m('iou'):5.3f}  {m('boundary_f1'):5.3f}  {m('precision'):5.3f}  {m('recall'):6.3f}"
        f" {m('area_error'):+5.2f}  {100 * s['dice_under_0.5']:5.1f} %"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--data", required=True, type=Path, help="folder written by the fetch script")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--pred", type=Path, help="folder of predicted masks, <dataset>/<id>.png")
    src.add_argument("--engine", action="store_true", help="run the engine's segmentation model")
    ap.add_argument(
        "--weights", type=Path, help="U-Net state dict for --engine (else its colour heuristic)"
    )
    ap.add_argument(
        "--max-side",
        type=int,
        default=1024,
        help="with --weights, segment photographs at most this many pixels on the long side "
        "and scale the mask back (default 1024; 0 keeps full size)",
    )
    ap.add_argument("--report", type=Path, help="report folder (default: DATA/reports/<run>)")
    ap.add_argument("--datasets", nargs="*", help="score only these datasets")
    ap.add_argument(
        "--all", action="store_true", help="also score photographs repeated across datasets"
    )
    a = ap.parse_args()
    if a.weights and not a.engine:
        ap.error("--weights goes with --engine")
    data = a.data.expanduser().resolve()
    weights = a.weights.expanduser().resolve() if a.weights else None
    pred = a.pred.expanduser().resolve() if a.pred else None
    run = f"engine-{weights.stem if weights else 'fallback'}" if a.engine else pred.name
    report = outside_git(a.report or data / "reports" / run)
    with open(data / "manifest.csv", newline="") as f:
        every = list(csv.DictReader(f))
    rows = select(every, a.datasets, a.all)
    if not rows:
        names = sorted({r["dataset"] for r in every})
        sys.exit(f"no photographs to score: the manifest's datasets are {', '.join(names)}")
    max_side = a.max_side if weights else 0  # the heuristic's baseline is at full size
    model = f"predictions in {pred}"
    engine = load_engine(weights) if a.engine else None
    report.mkdir(parents=True, exist_ok=True)
    if engine is not None:
        model = engine.version
        print(f"engine model: {model}", flush=True)
        pred = report / "pred"
        run_engine(engine, rows, data, pred, max_side)

    results = []
    for r in rows:
        truth = read_mask(data / r["mask"])
        p = pred / r["dataset"] / f"{r['id']}.png"
        if not p.exists():
            sys.exit(f"no prediction for {r['key']}: expected {p}")
        guess = read_mask(p)
        if guess.shape != truth.shape:
            sys.exit(f"{p}: {guess.shape[::-1]} pixels, the photograph is {truth.shape[::-1]}")
        frac = float(truth.mean())
        results.append(
            {
                "key": r["key"],
                "dataset": r["dataset"],
                "mask_target": r.get("mask_target") or "wound",
                "wound_fraction": frac,
                "band": next(name for lo, hi, name in BANDS if lo <= frac < hi),
                **score(guess, truth),
            }
        )

    with open(report / "scores.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0]))
        w.writeheader()
        w.writerows(
            {k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()} for r in results
        )
    pooled = [r for r in results if r["mask_target"] == "wound"]
    apart = sorted(
        {f"{r['dataset']} ({r['mask_target']})" for r in results if r["mask_target"] != "wound"}
    )
    groups = {"all": pooled}
    groups |= {
        f"dataset {d}": [r for r in results if r["dataset"] == d]
        for d in dict.fromkeys(r["dataset"] for r in results)
    }
    groups |= {f"wound {n}": [r for r in pooled if r["band"] == n] for _, _, n in BANDS}
    summary = {k: summarise(v) for k, v in groups.items() if v}
    human = clinicians(data)
    with open(report / "summary.json", "w") as f:
        json.dump(
            {
                "model": model,
                "photographs": len(results),
                "segmented_at_most_px": max_side if a.engine and max_side else None,
                "scored_apart": apart,
                "groups": summary,
                "clinician_pairwise_dice": spread(human) if human else None,
            },
            f,
            indent=1,
        )

    print(f"\n{model}: {len(results)} photographs\n")
    print(
        f"{'':28s} {'n':>4s}  {'Dice median [IQR]':19s}  {'IoU':5s}  {'BF1':5s}  {'prec.':5s}  "
        f"{'recall':6s} {'area':5s}  {'Dice<0.5':8s}"
    )
    for k, s in summary.items():
        print(line(k, s))
    if apart:
        print(f"\nscored in their own row only, not in 'all' or the size bands: {', '.join(apart)}")
    if human:
        h = spread(human)
        print(
            f"\nfor comparison, five clinicians against one another on LUTSeg's gold subset: Dice "
            f"median {h['median']:.3f} [{h['q1']:.3f}-{h['q3']:.3f}] over {h['n']} pairs"
        )
    print(f"\nreport: {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
