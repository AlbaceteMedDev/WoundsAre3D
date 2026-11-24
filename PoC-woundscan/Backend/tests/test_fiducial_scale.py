"""Synthetic check of fiducial_scale_check: a known plate at a known distance."""

import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fiducial_scale_check as fsc  # noqa: E402


def _scene(tmp_path, z_true_mm=160.0, lidar_bias=1.3, f=800.0):
    w, h = 1024, 768
    side_px = 80.0 * f / z_true_mm                       # 80 mm plate
    cx, cy = w / 2 + 20, h / 2 - 10
    im = Image.new("RGB", (w, h), (25, 25, 28))          # dark table
    d = ImageDraw.Draw(im)
    half = side_px / 2
    d.rectangle([cx - half, cy - half, cx + half, cy + half], fill=(205, 140, 110))   # orange plate
    dh = 0.8 * half                                       # 64 mm dot square
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = cx + sx * dh, cy + sy * dh
            d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(40, 40, 40))
    d.ellipse([cx - 60, cy - 45, cx + 60, cy + 45], fill=(150, 40, 40))   # wound
    work = tmp_path / "scan-0001"
    work.mkdir()
    im.save(work / "best_rgb.jpg", quality=95)
    depth = np.full((h, w), z_true_mm * lidar_bias / 1000.0, np.float32)
    np.savez(work / "preprocess.npz", depth_m=depth, valid=np.ones((h, w), bool),
             K=np.array([f, f, w / 2, h / 2]))
    return str(work)


def test_detects_dots_and_scale_error(tmp_path):
    work = _scene(tmp_path)
    r = fsc.check(work, 64.0, out_dir=str(tmp_path))
    assert r["status"] == "OK", r
    assert r["dotSource"] == "auto"
    assert abs(r["zFromDots_mm"] - 160.0) < 3.0
    assert abs(r["lidarScaleRatio"] - 1.3) < 0.03
    assert abs(r["zFromPlateEdge_mm"] - 160.0) < 8.0


def test_no_plate_reports_no_dots(tmp_path):
    work = tmp_path / "scan-0002"
    work.mkdir()
    Image.new("RGB", (1024, 768), (25, 25, 28)).save(work / "best_rgb.jpg")
    np.savez(work / "preprocess.npz", depth_m=np.full((768, 1024), 0.2, np.float32),
             valid=np.ones((768, 1024), bool), K=np.array([800.0, 800.0, 512.0, 384.0]))
    assert fsc.check(str(work), 64.0)["status"] == "NO_DOTS"
