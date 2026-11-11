"""Run the SEGMENT step's SAM logic on plain photos and render a contact sheet.

Uses the deployed SageMaker endpoint and the exact SEGMENT post-processing
(woundlib.segmentation: prompt, mask choice, clean-up).

Photos have no LiDAR depth and no known scale, so measurements are reported in
PIXELS of the 1024-px analysis image (length = max Feret diameter, width =
extent perpendicular to it, area = mask pixels), not mm / cm2. For images with an
expert mask, the same measurements are computed on the expert outline so SAM can
be compared like-for-like.

Colours: wound = red, non-wound = blue; white line = SAM outline, green line =
expert outline; yellow dot = prompt point.

    python sam_demo.py OUT_DIR --real "IMG|MASK" ... --phantom IMG ...
"""

import argparse
import csv
import io
import os
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lambdas", "step_functions", "shared"))
from woundlib import geometry, imaging, segmentation  # noqa: E402

os.environ.setdefault("SAGEMAKER_ENDPOINT_NAME", "wound-scan-poc-sam-endpoint")
os.environ.setdefault("AWS_PROFILE", "albacete")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

TILE_H = 360
WOUND = np.array([220, 30, 30])
NON_WOUND = np.array([30, 110, 230])


def font(px):
    try:
        return ImageFont.load_default(size=px)
    except TypeError:
        return ImageFont.load_default()


def prep(path):
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    w, h = imaging.analysis_size(*img.size)
    img = img.resize((w, h), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return img, buf.getvalue()


def segment(jpeg, shape, point):
    t = time.time()
    cands = segmentation.sam_predict(jpeg, point)
    dt = time.time() - t
    chosen = segmentation.choose_sam_mask(cands, point, shape)
    if chosen is None:
        return None, None, dt
    return segmentation.clean_mask(chosen[0], point), chosen[1], dt


def iou(a, b):
    u = (a | b).sum()
    return float((a & b).sum() / u) if u else 0.0


def measure_px(mask):
    """Length / width / area in pixels, same Feret method as COMPUTE."""
    c = imaging.trace_contour(mask)
    if len(c) < 3:
        return None
    L, p, q, d = geometry.feret(c)
    perp = np.array([-d[1], d[0]])
    proj = (c - c.mean(axis=0)) @ perp
    return {"length_px": L, "width_px": float(proj.max() - proj.min()), "area_px": int(mask.sum()),
            "area_pct": 100.0 * mask.sum() / mask.size, "axis": (p, q)}


def fmt_m(m):
    return f"L {m['length_px']:.0f} px | W {m['width_px']:.0f} px | A {m['area_px'] / 1000:.1f}k px ({m['area_pct']:.1f}%)"


def pct(a, b):
    return 100.0 * (a - b) / b if b else 0.0


def render(img, mask, gt, point, title, lines, outline_gt=True):
    """Colour wound red / non-wound blue using `mask` (or `gt` if mask is None)."""
    a = np.asarray(img).astype(np.float32).copy()
    seg = mask if mask is not None else gt
    if seg is not None:
        a[seg] = a[seg] * 0.45 + WOUND * 0.55
        a[~seg] = a[~seg] * 0.70 + NON_WOUND * 0.30
        m = measure_px(seg)
        if mask is not None:
            a[imaging.dilate(imaging.boundary(mask), 1)] = [255, 255, 255]
    if gt is not None and outline_gt:
        a[imaging.dilate(imaging.boundary(gt), 1)] = [40, 220, 90]
    im = Image.fromarray(a.astype(np.uint8))
    d = ImageDraw.Draw(im)
    if seg is not None and m:
        (x0, y0), (x1, y1) = m["axis"]
        d.line([(x0, y0), (x1, y1)], fill=(255, 235, 60), width=3)
    if point is not None:
        x, y = point
        r = max(6, im.width // 120)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 220, 0), outline=(0, 0, 0), width=2)
    s = TILE_H / im.height
    im = im.resize((int(im.width * s), TILE_H), Image.LANCZOS)
    head = 24 + 18 * len(lines)
    tile = Image.new("RGB", (max(im.width, 330), TILE_H + head + 6), "white")
    tile.paste(im, (0, head + 6))
    d = ImageDraw.Draw(tile)
    d.text((8, 4), title, fill=(20, 30, 40), font=font(16))
    for i, ln in enumerate(lines):
        d.text((8, 24 + 18 * i), ln, fill=(70, 80, 95), font=font(13))
    return tile


def row(tiles, pad=10):
    w = sum(t.width for t in tiles) + pad * (len(tiles) + 1)
    h = max(t.height for t in tiles) + 2 * pad
    out = Image.new("RGB", (w, h), (235, 238, 242))
    x = pad
    for t in tiles:
        out.paste(t, (x, pad))
        x += t.width + pad
    return out


def legend(width):
    im = Image.new("RGB", (width, 40), "white")
    d = ImageDraw.Draw(im)
    items = [((220, 30, 30), "wound"), ((30, 110, 230), "non-wound"), ((255, 255, 255), "SAM outline"),
             ((40, 220, 90), "expert outline"), ((255, 235, 60), "length axis"), ((255, 220, 0), "prompt point")]
    x = 12
    for col, label in items:
        d.rectangle([x, 12, x + 16, 28], fill=col, outline=(0, 0, 0))
        d.text((x + 22, 12), label, fill=(20, 30, 40), font=font(14))
        x += 40 + 8 * len(label)
    d.text((x + 10, 12), "measurements in pixels of the 1024-px image (no depth = no mm)", fill=(110, 110, 120), font=font(13))
    return im


def stack(rows, pad=6):
    w = max(r.width for r in rows)
    h = sum(r.height for r in rows) + pad * (len(rows) - 1)
    out = Image.new("RGB", (w, h), (235, 238, 242))
    y = 0
    for r in rows:
        out.paste(r, (0, y))
        y += r.height + pad
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--real", nargs="*", default=[])
    ap.add_argument("--phantom", nargs="*", default=[])
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rows, report = [], []

    for spec in a.real:
        ip, mp = spec.split("|")
        img, jpeg = prep(ip)
        gt = np.asarray(Image.open(mp).convert("L").resize(img.size, Image.NEAREST)) > 127
        name = os.path.basename(ip)
        h, w = gt.shape
        ys, xs = np.nonzero(gt)
        cy, cx = ys.mean(), xs.mean()
        k = int(np.argmin((xs - cx) ** 2 + (ys - cy) ** 2))
        prompts = (("image-centre prompt", (w / 2, h / 2)), ("prompt on wound", (float(xs[k]), float(ys[k]))))
        g = measure_px(gt)
        tiles = [render(img, None, gt, None, f"{name}  expert annotation", [fmt_m(g)], outline_gt=False)]
        report.append({"image": name, "source": "expert", **{k2: round(v, 1) for k2, v in g.items() if k2 != "axis"}})
        for label, pt in prompts:
            m, score, dt = segment(jpeg, (h, w), pt)
            if m is None:
                tiles.append(render(img, None, None, pt, f"SAM, {label}", ["no plausible mask", f"{dt:.1f}s"]))
                report.append({"image": name, "source": f"SAM {label}", "iou": 0})
                continue
            s = measure_px(m)
            j = iou(m, gt)
            lines = [fmt_m(s),
                     f"vs expert: L {pct(s['length_px'], g['length_px']):+.0f}%  W {pct(s['width_px'], g['width_px']):+.0f}%  "
                     f"A {pct(s['area_px'], g['area_px']):+.0f}%  IoU {j:.2f}"]
            tiles.append(render(img, m, gt, pt, f"SAM, {label} (score {score:.2f}, {dt:.0f}s)", lines))
            report.append({"image": name, "source": f"SAM {label}", "iou": round(j, 2), "sam_score": score,
                           **{k2: round(v, 1) for k2, v in s.items() if k2 != "axis"}})
            print(f"{name:12s} {label:20s} IoU={j:.2f}  SAM {fmt_m(s)}  | expert {fmt_m(g)}", flush=True)
        rows.append(row(tiles))

    for ip in a.phantom:
        img, jpeg = prep(ip)
        w, h = img.size
        pt = (w / 2, h / 2)
        m, score, dt = segment(jpeg, (h, w), pt)
        name = os.path.basename(ip)
        if m is None:
            tile = render(img, None, None, pt, "SAM, image-centre prompt", ["no plausible mask"])
        else:
            s = measure_px(m)
            tile = render(img, m, None, pt, f"SAM, image-centre prompt (score {score:.2f}, {dt:.0f}s)", [fmt_m(s)])
            report.append({"image": name, "source": "SAM image-centre prompt", "sam_score": score,
                           **{k2: round(v, 1) for k2, v in s.items() if k2 != "axis"}})
            print(f"{name:24s} SAM {fmt_m(s)}", flush=True)
        rows.append(row([render(img, None, None, None, f"{name}  photo", ["phantom kit (no expert outline)"]), tile]))

    sheet = stack([legend(max(r.width for r in rows))] + rows)
    path = os.path.join(a.out, "sam_demo.jpg")
    sheet.save(path, quality=88)
    for i, r in enumerate(rows):
        r.save(os.path.join(a.out, f"row_{i + 1}.jpg"), quality=88)
    keys = sorted({k for r in report for k in r}, key=lambda k: ["image", "source", "iou", "sam_score", "length_px",
                                                                  "width_px", "area_px", "area_pct"].index(k))
    with open(os.path.join(a.out, "measurements_px.csv"), "w", newline="") as f:
        wri = csv.DictWriter(f, fieldnames=keys)
        wri.writeheader()
        wri.writerows(report)
    print("wrote", path, sheet.size)


if __name__ == "__main__":
    main()
