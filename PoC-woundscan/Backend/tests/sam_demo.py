"""Run the SEGMENT step's SAM logic on plain photos and render a contact sheet.

Uses the deployed SageMaker endpoint and the exact SEGMENT post-processing
(woundlib.segmentation: centre-point prompt, mask choice, clean-up). Photos have
no LiDAR depth, so only the wound outline is shown (no mm / cm2, no 20 mm ring).

    python sam_demo.py OUT_DIR --real IMG:MASK ... --phantom IMG ...
"""

import argparse
import io
import os
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lambdas", "step_functions", "shared"))
from woundlib import imaging, segmentation  # noqa: E402

os.environ.setdefault("SAGEMAKER_ENDPOINT_NAME", "wound-scan-poc-sam-endpoint")
os.environ.setdefault("AWS_PROFILE", "albacete")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

TILE_H = 360


def font(px):
    try:
        return ImageFont.load_default(size=px)
    except TypeError:
        return ImageFont.load_default()


def prep(path):
    img = Image.open(path)
    from PIL import ImageOps
    img = ImageOps.exif_transpose(img).convert("RGB")
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


def render(img, mask, gt, point, title, sub):
    a = np.asarray(img).astype(np.float32).copy()
    if mask is not None:
        a[mask] = a[mask] * 0.55 + np.array([230, 40, 40]) * 0.45
        a[imaging.dilate(imaging.boundary(mask), 1)] = [255, 255, 255]
    if gt is not None:
        a[imaging.dilate(imaging.boundary(gt), 1)] = [40, 220, 90]
    im = Image.fromarray(a.astype(np.uint8))
    d = ImageDraw.Draw(im)
    x, y = point
    r = max(6, im.width // 120)
    d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 220, 0), outline=(0, 0, 0), width=2)
    s = TILE_H / im.height
    im = im.resize((int(im.width * s), TILE_H), Image.LANCZOS)
    tile = Image.new("RGB", (im.width, TILE_H + 52), "white")
    tile.paste(im, (0, 52))
    d = ImageDraw.Draw(tile)
    d.text((8, 6), title, fill=(20, 30, 40), font=font(17))
    d.text((8, 28), sub, fill=(90, 100, 110), font=font(14))
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
        gt = Image.open(mp).convert("L").resize(img.size, Image.NEAREST)
        gt = np.asarray(gt) > 127
        name = os.path.basename(ip)
        h, w = gt.shape
        centre = (w / 2, h / 2)
        ys, xs = np.nonzero(gt)
        # "aimed": the point inside the expert mask closest to its centroid
        cy, cx = ys.mean(), xs.mean()
        k = int(np.argmin((xs - cx) ** 2 + (ys - cy) ** 2))
        aimed = (float(xs[k]), float(ys[k]))
        tiles = [render(img, None, gt, centre, f"{name}  photo", "green = expert wound outline")]
        for label, pt in (("image-centre prompt", centre), ("prompt aimed at wound", aimed)):
            m, score, dt = segment(jpeg, (h, w), pt)
            j = iou(m, gt) if m is not None else 0.0
            sub = f"IoU vs expert {j:.2f} | SAM score {score or 0:.2f} | {dt:.1f}s" if m is not None else "no plausible mask"
            tiles.append(render(img, m, gt, pt, f"SAM ViT-B, {label}", sub))
            report.append((name, label, j, score, dt))
            print(f"{name:14s} {label:24s} IoU={j:.2f} score={score} {dt:.1f}s", flush=True)
        rows.append(row(tiles))

    for ip in a.phantom:
        img, jpeg = prep(ip)
        w, h = img.size
        centre = (w / 2, h / 2)
        m, score, dt = segment(jpeg, (h, w), centre)
        name = os.path.basename(ip)
        sub = f"SAM score {score or 0:.2f} | {dt:.1f}s" if m is not None else "no plausible mask"
        rows.append(row([render(img, None, None, centre, f"{name}  photo", "phantom kit (no ground truth)"),
                         render(img, m, None, centre, "SAM ViT-B, image-centre prompt", sub)]))
        print(f"{name:28s} centre score={score} {dt:.1f}s", flush=True)

    sheet = stack(rows)
    path = os.path.join(a.out, "sam_demo.jpg")
    sheet.save(path, quality=88)
    for i, r in enumerate(rows):
        r.save(os.path.join(a.out, f"row_{i + 1}.jpg"), quality=88)
    print("wrote", path, sheet.size)


if __name__ == "__main__":
    main()
