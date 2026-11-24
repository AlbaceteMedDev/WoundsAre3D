"""Check LiDAR scale against the phantom plates' fiducial dots.

The W-series phantom plates are 80 mm squares carrying four dots on a
concentric 64 mm square. Their spacing in the analysis image gives the true camera distance
(Z = side_mm * f / side_px); comparing it with the LiDAR depth at the dots
gives the scale error that inflates every pipeline length/width (area by its
square). Phantoms only: real wounds carry no fiducials.

Usage:
    # local replay output (tests/replay_local.py OUT_DIR)
    python fiducial_scale_check.py --work OUT_DIR/state/work [scanId-prefix ...]
    # straight from AWS (AWS_PROFILE must read the state/assets buckets)
    python fiducial_scale_check.py --s3 SCAN_ID [SCAN_ID ...]
    # detector failed: give the four dots in analysis pixels (TL TR BL BR)
    python fiducial_scale_check.py --work DIR c68f781e --dots 216,237,537,240,208,558,535,561

Writes <out>/fiducial_<id8>.jpg overlays (check them: a wrong square means a
wrong verdict) and <out>/fiducial_scale.json.
"""

import argparse
import io
import json
import os
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lambdas", "step_functions", "shared"))
from woundlib import imaging  # noqa: E402

DEFAULT_SPACING_MM = 64.0
STATE_BUCKET = "wound-scan-poc-sf-state-962524581373-us-east-1-an"
ASSETS_BUCKET = "wound-scan-poc-assets-962524581373-us-east-1-an"


# ----------------------------------------------------------------------------- inputs

def fetch_s3(scan_id, dst):
    import boto3
    s3 = boto3.client("s3")
    d = os.path.join(dst, scan_id)
    os.makedirs(d, exist_ok=True)
    for bucket, key, name in [
        (STATE_BUCKET, f"work/{scan_id}/preprocess.npz", "preprocess.npz"),
        (STATE_BUCKET, f"work/{scan_id}/best_rgb.jpg", "best_rgb.jpg"),
        (STATE_BUCKET, f"work/{scan_id}/segment.npz", "segment.npz"),
        (ASSETS_BUCKET, f"processed/{scan_id}/measurements.json", "measurements.json"),
    ]:
        try:
            s3.download_file(bucket, key, os.path.join(d, name))
        except Exception as e:  # measurements may be missing for FAILED scans
            if name not in ("measurements.json", "segment.npz"):
                raise RuntimeError(f"cannot fetch s3://{bucket}/{key}: {e}")
    return d


def load_measurements(work_dir, results):
    p = os.path.join(work_dir, "measurements.json")
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return results.get(os.path.basename(work_dir)[:8])


# ----------------------------------------------------------------------------- detection
#
# Plate first, then dots: the W plates are 80 mm squares with the four dots on a
# concentric 64 mm square (ratio 0.80, measured on all 8 plates). The plate is
# grown from the wound mask over plate-coloured pixels, its outline fitted with a
# minimum-area rectangle, and each dot searched near its predicted position.

DOT_TO_PLATE = 0.80


def load_wound(work_dir, shape):
    p = os.path.join(work_dir, "segment.npz")
    if os.path.exists(p):
        z = np.load(p)
        sh = tuple(int(v) for v in z["shape"])
        return np.unpackbits(z["wound"])[: sh[0] * sh[1]].reshape(sh).astype(bool)
    return None


def _order(P):
    """Order four corners TL, TR, BL, BR (image is roughly upright; plates tilt < 45 deg)."""
    P = np.asarray(P, float)
    c = P.mean(0)
    ang = np.arctan2(P[:, 1] - c[1], P[:, 0] - c[0])      # -pi..pi, y down
    out = {}
    for p, a in zip(P, ang):
        key = ("T" if a < 0 else "B") + ("L" if abs(a) > np.pi / 2 else "R")
        out[key] = p
    if len(out) < 4:                                          # exactly on an axis: fall back to sums
        s, d = P.sum(1), P[:, 0] - P[:, 1]
        return np.array([P[s.argmin()], P[d.argmax()], P[d.argmin()], P[s.argmax()]])
    return np.array([out["TL"], out["TR"], out["BL"], out["BR"]])


def _disc(shape, r=40):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    return (xx - w / 2) ** 2 + (yy - h / 2) ** 2 < r ** 2


def plate_mask(rgb, seed):
    """Plate-coloured region connected to a band just outside `seed`."""
    f = rgb.astype(float)
    chrom = f[..., :2] / (f.sum(2) + 1)[..., None]
    bri = f.mean(2)
    band = imaging.dilate(seed, 30) & ~imaging.dilate(seed, 12)
    if band.sum() < 50:
        return None
    c0, b0 = np.median(chrom[band], 0), np.median(bri[band])
    sim = (np.linalg.norm(chrom - c0, axis=2) < 0.035) & (bri > 0.6 * b0) & (bri < 1.4 * b0)
    sim = imaging.open_close(sim | seed, 2)
    lab = imaging.label(sim)
    ids = lab[band & sim]
    ids = ids[ids > 0]
    if ids.size == 0:
        return None
    return imaging.fill_holes(lab == np.bincount(ids).argmax())


def _hull(P):
    P = sorted(set(map(tuple, P)))
    cr = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in P:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(up) >= 2 and cr(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return np.array(lo[:-1] + up[:-1], float)


def _min_rect(H):
    best = None
    for k in range(len(H)):
        e = H[(k + 1) % len(H)] - H[k]
        n = np.linalg.norm(e)
        if n == 0:
            continue
        u = e / n
        v = np.array([-u[1], u[0]])
        a, b = H @ u, H @ v
        area = np.ptp(a) * np.ptp(b)
        if best is None or area < best[0]:
            best = (area, u, v, a.min(), a.max(), b.min(), b.max())
    _, u, v, a0, a1, b0, b1 = best
    return np.array([a * u + b * v for a, b in [(a0, b0), (a1, b0), (a1, b1), (a0, b1)]])


def find_plate(rgb, wound):
    """Plate rectangle corners (TL, TR, BL, BR) or None."""
    h, w = rgb.shape[:2]
    for seed in ([wound] if wound is not None and wound.any() else []) + [_disc((h, w))]:
        pm = plate_mask(rgb, seed)
        if pm is None:
            continue
        frac = pm.mean()
        if not 0.03 <= frac <= 0.6 or imaging.boundary(pm)[[0, -1], :].any() or imaging.boundary(pm)[:, [0, -1]].any():
            continue
        ys, xs = np.nonzero(imaging.boundary(pm))
        R = _min_rect(_hull(np.c_[xs, ys]))
        sides = [np.linalg.norm(R[i] - R[(i + 1) % 4]) for i in range(4)]
        fill = pm.sum() / (sides[0] * sides[1])
        if max(sides) / min(sides) > 1.15 or fill < 0.55:       # not a square plate (glare can hide part of it)
            continue
        return _order(R)
    return None


def find_dot_square(rgb, wound=None):
    """(dots TL TR BL BR, plate corners) or (None, plate-or-None)."""
    R = find_plate(rgb, wound)
    if R is None:
        return None, None
    c = R.mean(0)
    pred = c + DOT_TO_PLATE * (R - c)
    side = np.mean([np.linalg.norm(R[0] - R[1]), np.linalg.norm(R[2] - R[3])])
    gray = rgb.astype(float).mean(2)
    return refine(gray, pred, r=max(8, int(0.045 * side))), R


def refine(gray, P, r=14):
    """Snap each dot to the centroid of its strongest local-contrast pixels."""
    bg = np.asarray(Image.fromarray(gray.astype(np.uint8)).filter(ImageFilter.MedianFilter(15))).astype(float)
    out = []
    for x, y in P:
        x, y = int(round(x)), int(round(y))
        y0, x0 = max(0, y - r), max(0, x - r)
        dev = np.abs(gray[y0:y + r, x0:x + r] - bg[y0:y + r, x0:x + r])
        m = dev >= np.sort(dev.ravel())[-25]
        ys, xs = np.nonzero(m)
        out.append([x0 + xs.mean(), y0 + ys.mean()])
    return np.array(out)


# ----------------------------------------------------------------------------- check

def check(work_dir, spacing_mm, dots=None, results=None, out_dir=None):
    z = np.load(os.path.join(work_dir, "preprocess.npz"))
    depth = z["depth_m"] * 1000.0
    valid = z["valid"].astype(bool)
    fx, fy, cx, cy = [float(v) for v in z["K"]]
    rgb = np.asarray(Image.open(os.path.join(work_dir, "best_rgb.jpg")).convert("RGB"))
    gray = rgb.astype(float).mean(2)
    sid = os.path.basename(os.path.normpath(work_dir))
    res = {"scanId": sid}

    plate = None
    if dots is not None:
        P, source = refine(gray, _order(np.array(dots, float).reshape(4, 2))), "manual"
    else:
        P, plate = find_dot_square(rgb, load_wound(work_dir, gray.shape))
        source = "auto"
    if P is None:
        res["status"] = "NO_DOTS"
        return res

    sides = np.array([np.linalg.norm(P[a] - P[b]) for a, b in [(0, 1), (2, 3), (0, 2), (1, 3)]])
    diag = np.array([np.linalg.norm(P[0] - P[3]), np.linalg.norm(P[1] - P[2])])
    side_px = float(sides.mean())
    f = (fx + fy) / 2.0
    z_dots = spacing_mm * f / side_px

    def z_at(p, r=6):
        x, y = int(p[0]), int(p[1])
        a, v = depth[y - r:y + r, x - r:x + r], valid[y - r:y + r, x - r:x + r]
        return float(np.median(a[v])) if v.any() else float("nan")

    z_lidar_dots = np.array([z_at(p) for p in P])
    c = P.mean(0).astype(int)
    span = int(side_px * 0.12)
    centre = depth[c[1] - span:c[1] + span, c[0] - span:c[0] + span]
    centre_v = valid[c[1] - span:c[1] + span, c[0] - span:c[0] + span]
    z_lidar_centre = float(np.median(centre[centre_v])) if centre_v.any() else float("nan")
    ratio = z_lidar_centre / z_dots

    res.update({
        "status": "OK",
        "dotSource": source,
        "dots_px": P.round(1).tolist(),
        "side_px": round(side_px, 1),
        "squareness": round(float(diag.mean() / side_px / np.sqrt(2)), 3),   # 1.000 = perfect square
        "sideSpread": round(float(np.ptp(sides) / side_px), 3),
        "zFromDots_mm": round(z_dots, 1),
        "zLidarAtDots_mm": np.round(z_lidar_dots, 1).tolist(),
        "zLidarCentre_mm": round(z_lidar_centre, 1),
        "lidarScaleRatio": round(ratio, 3),                                   # >1: lengths inflated
        "lidarLeftRightRamp_mm": round(float((z_lidar_dots[1] + z_lidar_dots[3] - z_lidar_dots[0] - z_lidar_dots[2]) / 2), 1),
    })
    if plate is not None:
        pside = float(np.mean([np.linalg.norm(plate[a] - plate[b]) for a, b in [(0, 1), (2, 3), (0, 2), (1, 3)]]))
        res["zFromPlateEdge_mm"] = round(spacing_mm / DOT_TO_PLATE * f / pside, 1)   # independent check, edges are softer
    if res["squareness"] < 0.97 or res["squareness"] > 1.03 or res["sideSpread"] > 0.12:
        res["status"] = "SUSPECT_SQUARE"
    m = load_measurements(work_dir, results or {})
    if m and m.get("length_mm"):
        res["pipeline"] = {k: m.get(k) for k in ("length_mm", "width_mm", "bed_area_cm2")}
        res["corrected"] = {
            "length_mm": round(m["length_mm"] / ratio, 1),
            "width_mm": round(m["width_mm"] / ratio, 1),
            "bed_area_cm2": round(m["bed_area_cm2"] / ratio ** 2, 2),
        }

    if out_dir:
        im = Image.fromarray(rgb)
        d = ImageDraw.Draw(im)
        for x, y in P:
            d.ellipse([x - 10, y - 10, x + 10, y + 10], outline=(0, 255, 0), width=3)
        d.line([tuple(P[0]), tuple(P[1]), tuple(P[3]), tuple(P[2]), tuple(P[0])], fill=(0, 255, 0), width=1)
        if plate is not None:
            d.line([tuple(plate[0]), tuple(plate[1]), tuple(plate[3]), tuple(plate[2]), tuple(plate[0])], fill=(0, 160, 255), width=2)
        d.rectangle([0, 0, im.width, 26], fill=(0, 0, 0))
        d.text((6, 6), f"{sid[:8]}  Z dots {z_dots:.0f} mm  LiDAR {z_lidar_centre:.0f} mm  ratio {ratio:.2f}  {res['status']}",
               fill=(255, 255, 0))
        im.save(os.path.join(out_dir, f"fiducial_{sid[:8]}.jpg"), quality=88)
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--work", help="directory holding <scanId>/preprocess.npz + best_rgb.jpg")
    src.add_argument("--s3", action="store_true", help="fetch the listed scan ids from AWS")
    ap.add_argument("ids", nargs="*", help="scan ids (or 8-char prefixes with --work); default: all in --work")
    ap.add_argument("--spacing-mm", type=float, default=DEFAULT_SPACING_MM)
    ap.add_argument("--dots", help="x1,y1,...,x4,y4 analysis-pixel dot centres (single scan only)")
    ap.add_argument("--results", help="replay results.json to pick up pipeline measurements")
    ap.add_argument("--out", default=".", help="where to write overlays and fiducial_scale.json")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    results = {}
    if a.results:
        with open(a.results) as f:
            results = {r["scanId"][:8]: r.get("measurements") for r in json.load(f)}

    if a.s3:
        if not a.ids:
            ap.error("--s3 needs scan ids")
        tmp = tempfile.mkdtemp(prefix="fiducial_")
        dirs = [fetch_s3(i, tmp) for i in a.ids]
    else:
        names = sorted(n for n in os.listdir(a.work) if os.path.exists(os.path.join(a.work, n, "preprocess.npz")))
        if a.ids:
            names = [n for n in names if any(n.startswith(i) for i in a.ids)]
        dirs = [os.path.join(a.work, n) for n in names]
    dots = [float(v) for v in a.dots.split(",")] if a.dots else None
    if dots and len(dirs) != 1:
        ap.error("--dots needs exactly one scan")

    rows = []
    for d in dirs:
        r = check(d, a.spacing_mm, dots, results, a.out)
        rows.append(r)
        if r["status"] == "NO_DOTS":
            print(f"{r['scanId'][:8]}  NO_DOTS (not a fiducial plate, or pass --dots)")
            continue
        line = (f"{r['scanId'][:8]}  {r['status']:14} Z dots {r['zFromDots_mm']:6.1f}  LiDAR {r['zLidarCentre_mm']:6.1f}  "
                f"ratio {r['lidarScaleRatio']:.3f}  ramp {r['lidarLeftRightRamp_mm']:+.0f} mm")
        if "corrected" in r:
            p, c = r["pipeline"], r["corrected"]
            line += f"  L x W {p['length_mm']} x {p['width_mm']} -> {c['length_mm']} x {c['width_mm']} mm"
        print(line)
    ok = [r["lidarScaleRatio"] for r in rows if r["status"] == "OK"]
    if ok:
        print(f"\n{len(ok)} plates: LiDAR/true distance ratio mean {np.mean(ok):.3f}, range {min(ok):.3f}-{max(ok):.3f}")
    with open(os.path.join(a.out, "fiducial_scale.json"), "w") as f:
        json.dump(rows, f, indent=2)


if __name__ == "__main__":
    main()
