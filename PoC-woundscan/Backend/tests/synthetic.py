"""Synthetic wound-phantom capture bundles in the exact iOS upload format.

Each bundle is 25 files: frame_{1..5}_{rgb.jpg,depth.bin,confidence.bin,intrinsics.json,metadata.json}
with ARKit conventions (RGB 3840x2160 landscape sensor orientation, float32 depth in
metres on a 256x144 grid covering the same field of view, uint8 confidence 0-2).

Geometry: a skin plane at `distance_mm`, tilted by `tilt_deg`, with an elliptical
cavity (semi-axes a, b) whose floor is a paraboloid of depth `depth_mm`.
Ground truth (exact for this geometry):
    length = 2a, width = 2b, bed area = pi*a*b,
    depth  = depth_mm,
    peri-wound area = perimeter*20 + pi*20^2   (outer offset of a convex curve).

Usage:
    python synthetic.py OUT_DIR [--length 42.3 --width 28.7 --depth 6.2 --tilt 8]
"""

import argparse
import io
import json
import math
import os

import numpy as np
from PIL import Image, ImageFilter

RGB_W, RGB_H = 3840, 2160
DEPTH_W, DEPTH_H = 256, 144
FX = FY = 2722.7
CX, CY = 1930.2, 1090.3


def ellipse_perimeter(a, b):
    h = ((a - b) / (a + b)) ** 2
    return math.pi * (a + b) * (1 + 3 * h / (10 + math.sqrt(4 - 3 * h)))


def ground_truth(length, width, depth):
    a, b = length / 2, width / 2
    bed = math.pi * a * b
    peri = ellipse_perimeter(a, b) * 20 + math.pi * 400
    return {"length_mm": length, "width_mm": width, "bed_area_cm2": bed / 100,
            "depth_mm": depth, "peri_wound_area_cm2": peri / 100}


def _surface(w, h, fx, fy, cx, cy, distance, tilt_deg, a, b, depth, rot_deg):
    """Ray-cast the phantom. Returns z (mm) and a wound mask for a w x h camera."""
    t = math.radians(tilt_deg)
    n = np.array([0.0, math.sin(t), -math.cos(t)])          # plane normal (towards camera)
    p0 = np.array([0.0, 0.0, distance])                       # wound centre on the plane
    e1 = np.array([1.0, 0.0, 0.0])
    e2 = np.cross(n, e1)
    r = math.radians(rot_deg)
    ax1 = math.cos(r) * e1 + math.sin(r) * e2                 # ellipse major axis
    ax2 = np.cross(n, ax1)
    u = (np.arange(w, dtype=np.float64)[None, :] - cx) / fx
    v = (np.arange(h, dtype=np.float64)[:, None] - cy) / fy
    rx, ry = u + 0 * v, v + 0 * u
    denom = n[0] * rx + n[1] * ry + n[2]                      # n . (rx, ry, 1), negative
    tt = (n @ p0) / denom
    X = np.stack([rx * tt, ry * tt, tt], -1) - p0
    s1, s2 = X @ ax1, X @ ax2
    q = (s1 / a) ** 2 + (s2 / b) ** 2
    inside = q < 1
    rec = np.where(inside, depth * (1 - q), 0.0)              # recess below the plane (mm)
    # Move along the viewing ray so the point lies exactly `rec` below the plane:
    # signed distance of r*z to the plane is (n.r)*(z - tt) = -rec.
    z = tt + rec / (-denom)
    return z, inside


def make_bundle(out_dir, length=42.3, width=28.7, depth=6.2, distance=220.0, tilt=8.0, rot=20.0,
                noise_mm=0.4, seed=1, sharp_frame=4):
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(seed)
    a, b = length / 2, width / 2
    # Depth grid (same field of view, scaled intrinsics).
    sx, sy = DEPTH_W / RGB_W, DEPTH_H / RGB_H
    zd, _ = _surface(DEPTH_W, DEPTH_H, FX * sx, FY * sy, (CX + .5) * sx - .5, (CY + .5) * sy - .5,
                     distance, tilt, a, b, depth, rot)
    # RGB rendered at 1920x1080 then upscaled.
    lw, lh = RGB_W // 2, RGB_H // 2
    zr, inside = _surface(lw, lh, FX / 2, FY / 2, (CX + .5) / 2 - .5, (CY + .5) / 2 - .5,
                          distance, tilt, a, b, depth, rot)
    skin = np.array([224, 182, 160], dtype=np.float64)
    bed = np.array([150, 40, 45], dtype=np.float64)
    tex = rng.normal(0, 6, (lh, lw, 1))
    img = np.where(inside[..., None], bed, skin) + tex
    shade = np.clip(1 - (zr - distance) / 80, 0.75, 1.05)[..., None]
    img = np.clip(img * shade, 0, 255).astype(np.uint8)
    base = Image.fromarray(img).resize((RGB_W, RGB_H), Image.BICUBIC)

    gt = ground_truth(length, width, depth)
    for i in range(1, 6):
        blur = 0 if i == sharp_frame else 2.5 + abs(i - sharp_frame)
        im = base.filter(ImageFilter.GaussianBlur(blur)) if blur else base
        im.save(os.path.join(out_dir, f"frame_{i}_rgb.jpg"), quality=90)
        d = (zd + rng.normal(0, noise_mm, zd.shape)) / 1000.0
        d.astype("<f4").tofile(os.path.join(out_dir, f"frame_{i}_depth.bin"))
        conf = np.full((DEPTH_H, DEPTH_W), 2, dtype=np.uint8)
        conf[rng.random(conf.shape) < 0.05] = 0
        conf.tofile(os.path.join(out_dir, f"frame_{i}_confidence.bin"))
        with open(os.path.join(out_dir, f"frame_{i}_intrinsics.json"), "w") as f:
            json.dump({"fx": FX, "fy": FY, "cx": CX, "cy": CY, "width": RGB_W, "height": RGB_H}, f)
        with open(os.path.join(out_dir, f"frame_{i}_metadata.json"), "w") as f:
            json.dump({"frameIndex": i, "timestamp": 1000.0 + 0.5 * i, "deviceOrientation": "portrait",
                       "capturedAt": "2026-11-11T12:00:00Z", "synthetic": True}, f)
    with open(os.path.join(out_dir, "ground_truth.json"), "w") as f:
        json.dump({"params": {"length": length, "width": width, "depth": depth, "distance_mm": distance,
                              "tilt_deg": tilt, "rotation_deg": rot, "noise_mm": noise_mm,
                              "sharp_frame": sharp_frame}, "expected": gt}, f, indent=2)
    return gt


PRESETS = {
    # name: (length, width, depth, distance, tilt, rotation)
    "ellipse-42x29x6": (42.3, 28.7, 6.2, 220, 8, 20),
    "round-30x30x4": (30.0, 30.0, 4.0, 200, 0, 0),
    "long-60x20x3": (60.0, 20.0, 3.0, 260, 15, -35),
}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--preset", choices=sorted(PRESETS), default=None)
    ap.add_argument("--length", type=float, default=42.3)
    ap.add_argument("--width", type=float, default=28.7)
    ap.add_argument("--depth", type=float, default=6.2)
    ap.add_argument("--distance", type=float, default=220)
    ap.add_argument("--tilt", type=float, default=8)
    ap.add_argument("--rot", type=float, default=20)
    a = ap.parse_args()
    if a.preset:
        L, W, D, dist, tilt, rot = PRESETS[a.preset]
    else:
        L, W, D, dist, tilt, rot = a.length, a.width, a.depth, a.distance, a.tilt, a.rot
    print(json.dumps(make_bundle(a.out, L, W, D, dist, tilt, rot), indent=2))
