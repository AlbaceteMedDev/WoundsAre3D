"""Score wound segmentation on the real-wound test set that
fetch_wound_segmentation_data.py lays out.

    python scripts/evaluate_segmentation.py --data DIR --pred PRED
    python scripts/evaluate_segmentation.py --data DIR --engine [--weights boundary_v1.pt]

PRED holds one mask per photograph, PRED/<dataset>/<id>.png, at the
photograph's size and non-zero where the model sees wound. --engine runs the
engine's BoundarySegmentationModel instead and keeps its masks in
REPORT/pred/. A photograph that two datasets publish is scored once, from the
dataset listed first in the manifest (--all scores both copies).

Per photograph: Dice, IoU, precision, recall, boundary F1 (boundary pixels
within 0.75 % of the image diagonal of the other boundary) and the signed
error in wound area. Printed per dataset and by the wound's share of the
frame, as medians and quartiles with the share of photographs under Dice 0.5,
and written to REPORT/scores.csv and REPORT/summary.json. Where LUTSeg's
five-clinician subset is present, the clinicians' agreement with one another
is printed too: about as well as a model can be expected to do.
"""

from __future__ import annotations

import argparse
import csv
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


def read_mask(path: Path) -> np.ndarray:
    a = np.asarray(Image.open(path))
    return (a[..., :3].max(axis=2) if a.ndim == 3 else a) > 0


def edge(m: np.ndarray) -> np.ndarray:
    return m & ~ndimage.binary_erosion(m, border_value=0)


def score(pred: np.ndarray, truth: np.ndarray) -> dict[str, float]:
    """Overlap, boundary and area agreement of a predicted mask with the truth."""
    inter, p, t = float((pred & truth).sum()), float(pred.sum()), float(truth.sum())
    nan = float("nan")
    out = {
        "dice": 2 * inter / (p + t) if p + t else 1.0,
        "iou": inter / (p + t - inter) if p + t else 1.0,
        "precision": inter / p if p else nan,
        "recall": inter / t if t else nan,
        "area_error": (p - t) / t if t else nan,
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


def run_engine(rows: list[dict[str, str]], data: Path, dest: Path, weights: Path | None) -> str:
    """Segment every photograph with the engine's model; masks go to dest."""
    sys.path.insert(0, str(ENGINE / "src"))
    from woundscan.ml.boundary_segmentation import BoundarySegmentationModel

    model = (
        BoundarySegmentationModel.from_weights(weights)
        if weights
        else BoundarySegmentationModel.fallback()
    )
    print(f"engine model: {model.version}", flush=True)
    for i, r in enumerate(rows, 1):
        rgb = np.asarray(Image.open(data / r["image"]).convert("RGB"))
        mask = model.segment(rgb).binary_mask
        out = dest / r["dataset"] / f"{r['id']}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(np.where(mask, 255, 0).astype(np.uint8), mode="L").save(out)
        if i % 25 == 0 or i == len(rows):
            print(f"  segmented {i}/{len(rows)}", flush=True)
    return model.version


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
    d, b, a = s["dice"], s["boundary_f1"], s["area_error"]
    return (
        f"{name:28s} {s['n']:4d}  {d['median']:.3f} [{d['q1']:.3f}-{d['q3']:.3f}]  "
        f"{s['iou']['median']:.3f}  {b['median']:.3f}  {s['precision'].get('median', float('nan')):.3f}"
        f"  {s['recall']['median']:.3f}  {a['median']:+.2f}  {100 * s['dice_under_0.5']:5.1f} %"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--data", required=True, type=Path, help="folder written by the fetch script")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--pred", type=Path, help="folder of predicted masks, <dataset>/<id>.png")
    src.add_argument("--engine", action="store_true", help="run the engine's segmentation model")
    ap.add_argument("--weights", type=Path, help="U-Net weights for --engine (else its fallback)")
    ap.add_argument("--report", type=Path, default=Path("segmentation_report"))
    ap.add_argument("--datasets", nargs="*", help="score only these datasets")
    ap.add_argument(
        "--all", action="store_true", help="also score photographs repeated across datasets"
    )
    a = ap.parse_args()
    data = a.data.expanduser()
    with open(data / "manifest.csv", newline="") as f:
        rows = [
            r
            for r in csv.DictReader(f)
            if (a.all or not r["duplicate_of"]) and (not a.datasets or r["dataset"] in a.datasets)
        ]
    a.report.mkdir(parents=True, exist_ok=True)
    model = "predictions in " + str(a.pred)
    pred = a.pred
    if a.engine:
        pred = a.report / "pred"
        model = run_engine(rows, data, pred, a.weights)

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
        band = next(name for lo, hi, name in BANDS if lo <= frac < hi)
        results.append(
            dict(
                key=r["key"],
                dataset=r["dataset"],
                wound_fraction=frac,
                band=band,
                **score(guess, truth),
            )
        )

    with open(a.report / "scores.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["key", "dataset", "wound_fraction", "band", *METRICS])
        w.writeheader()
        w.writerows(
            {k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()} for r in results
        )
    groups = {"all": results}
    groups |= {
        f"dataset {d}": [r for r in results if r["dataset"] == d]
        for d in dict.fromkeys(r["dataset"] for r in results)
    }
    groups |= {f"wound {n}": [r for r in results if r["band"] == n] for _, _, n in BANDS}
    summary = {k: summarise(v) for k, v in groups.items() if v}
    human = clinicians(data)
    print(f"\n{model}: {len(results)} photographs\n")
    print(
        f"{'':28s} {'n':>4s}  {'Dice median [IQR]':22s}  {'IoU':5s}  {'BF1':5s}  {'prec.':5s}  "
        f"{'recall':6s} {'area':5s}  {'Dice<0.5':8s}"
    )
    for k, s in summary.items():
        print(line(k, s))
    if human:
        h = spread(human)
        print(
            f"\nfor comparison, five clinicians against one another on LUTSeg's gold subset: Dice "
            f"median {h['median']:.3f} [{h['q1']:.3f}-{h['q3']:.3f}] over {h['n']} pairs"
        )
    with open(a.report / "summary.json", "w") as f:
        json.dump(
            {
                "model": model,
                "photographs": len(results),
                "groups": summary,
                "clinician_pairwise_dice": spread(human) if human else None,
            },
            f,
            indent=1,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
