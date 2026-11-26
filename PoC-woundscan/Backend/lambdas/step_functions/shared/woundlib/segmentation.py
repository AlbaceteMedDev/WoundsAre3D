"""Wound segmentation: SAM ViT-B on SageMaker Serverless with a centre-point prompt,
plus a depth-based fallback used only after the SAM retries are exhausted."""

import base64
import io
import json
import os

import boto3
import numpy as np
from botocore.config import Config

from . import geometry, imaging

MIN_AREA_FRACTION = 0.0005   # 0.05 % of the analysis frame
MAX_AREA_FRACTION = 0.50     # large wounds framed close-up can fill up to half the frame
FALLBACK_MAX_FRACTION = 0.12
FALLBACK_MAX_PLANE_RMSE_MM = 1.5

_smr = None


def _runtime():
    global _smr
    if _smr is None:
        # Serverless cold starts can take 30-90 s (SOW 2.2); keep the read timeout above that.
        _smr = boto3.client("sagemaker-runtime", config=Config(read_timeout=120, retries={"max_attempts": 1}))
    return _smr


def endpoint_name():
    v = os.environ.get("SAGEMAKER_ENDPOINT_NAME") or os.environ.get("SAGEMAKER_ENDPOINT_ARN", "")
    return v.split("/")[-1] if v else ""


def _unwrap(out):
    """The HF inference toolkit JSON-encodes transform_fn's (body, content_type)
    tuple as a 2-item list; accept that, a JSON string, or the plain dict."""
    for _ in range(3):
        if isinstance(out, list) and out and isinstance(out[0], str):
            out = out[0]
        if isinstance(out, str):
            out = json.loads(out)
        if isinstance(out, dict):
            return out
    raise ValueError(f"unexpected SAM response type {type(out).__name__}")


def sam_predict(jpeg_bytes, point_xy, negative_points=()):
    """Call the SAM endpoint with one positive point and optional negative points
    (pixels of the submitted image). Returns a list of (mask bool array, score)."""
    pts = [[float(point_xy[0]), float(point_xy[1])]] + [[float(x), float(y)] for x, y in negative_points]
    body = {
        "image": base64.b64encode(jpeg_bytes).decode("ascii"),
        "points": pts,
        "labels": [1] + [0] * len(negative_points),
        "multimask_output": True,
    }
    resp = _runtime().invoke_endpoint(
        EndpointName=endpoint_name(),
        ContentType="application/json",
        Accept="application/json",
        Body=json.dumps(body).encode("utf-8"),
    )
    out = _unwrap(json.loads(resp["Body"].read()))
    masks = []
    for m_b64, score in zip(out["masks"], out["scores"]):
        masks.append((imaging.png_to_mask(base64.b64decode(m_b64)), float(score)))
    return masks


def choose_sam_mask(candidates, point_xy, shape):
    """Pick the best SAM candidate: contains the prompt, plausible size, highest score,
    and not hugging the image border (which would mean SAM picked the background)."""
    h, w = shape
    total = h * w
    px, py = int(round(point_xy[0])), int(round(point_xy[1]))
    best, best_key = None, None
    for m, score in candidates:
        if m.shape != shape:
            m = imaging.resample_nearest(m.astype(np.uint8), w, h) > 0
        frac = m.sum() / total
        if not (MIN_AREA_FRACTION <= frac <= MAX_AREA_FRACTION):
            continue
        border = np.concatenate([m[0], m[-1], m[:, 0], m[:, -1]]).mean()
        contains = bool(m[min(py, h - 1), min(px, w - 1)])
        key = (contains, border < 0.05, score)
        if best_key is None or key > best_key:
            best, best_key = (m, score), key
    return best


# ---------------------------------------------------------------- wound locator
#
# The centre-point prompt alone fails when the wound is not exactly centred: SAM's
# most confident mask is then the whole phantom plate / limb (or the table). The
# locator first finds the surface the wound sits on (the "container": the plate or
# skin region) from SAM's first-pass masks, then the most salient compact region
# on it (colour difference + LiDAR relief against a local surface fit, weighted
# towards the container centre). That region steers a second SAM prompt and is
# used to pick SAM's mask by overlap. All locator work runs at 1/LOCATOR_SCALE.

LOCATOR_SCALE = 4
CONTAINER_MIN_FRACTION, CONTAINER_MAX_FRACTION = 0.02, 0.60
CONTAINER_MIN_SOLIDITY, CONTAINER_MAX_ASPECT = 0.85, 2.5
BLOB_MIN_FRACTION, BLOB_MAX_FRACTION = 0.004, 0.60     # of the container (small wounds ~0.5 %)
BLOB_MERGE_PX = 3              # join salient fragments this close (locator px) into one region
BLOB_MIN_COLOUR = 0.30         # mean normalised colour difference; relief-only blobs are
                               # engraved marks (scale bar, text) or LiDAR noise, not wounds
WOUND_MAX_CONTAINER_FRACTION = 0.60                     # larger = SAM took the plate
MIN_BLOB_IOU = 0.20
MIN_BLOB_COVER, MAX_GROWTH = 0.70, 6.0   # or: mask holds >= 70 % of the seed, <= 6x its area
RELIEF_NOISE_MM = 0.0          # LiDAR relief below this is ignored
RELIEF_FLOOR_MM = 0.8          # relief normaliser floor, so flat surfaces add no saliency
RELIEF_WEIGHT = 1.0
SALIENCY_PERCENTILE = 75
CENTRE_SIGMA = 0.20            # centre prior, as a fraction of the container size
MIN_WOUND_SOLIDITY = 0.60      # ragged masks are background/texture, not a wound


def _largest_component(m):
    lab = imaging.label(m)
    if lab.max() == 0:
        return m
    counts = np.bincount(lab.ravel())
    counts[0] = 0
    return lab == int(np.argmax(counts))


def _hull_area(m):
    ys, xs = np.nonzero(imaging.boundary(m))
    pts = sorted(set(zip(xs.tolist(), ys.tolist())))
    if len(pts) < 3:
        return float(max(1, m.sum()))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = np.array(lower[:-1] + upper[:-1], dtype=np.float64)
    x, y = hull[:, 0], hull[:, 1]
    return float(max(1.0, 0.5 * abs(x @ np.roll(y, 1) - y @ np.roll(x, 1))))


def shape_stats(m):
    """(solidity, aspect ratio) of a mask."""
    ys, xs = np.nonzero(m)
    if ys.size < 5:
        return 0.0, 99.0
    ev = np.sort(np.linalg.eigvalsh(np.cov(np.stack([xs, ys]).astype(np.float64))))
    return float(m.sum() / _hull_area(m)), float(np.sqrt(ev[1] / max(ev[0], 1e-6)))


def _touches_border(m, tol=0.02):
    return float(np.concatenate([m[0], m[-1], m[:, 0], m[:, -1]]).mean()) > tol


def find_container(candidates_small):
    """The plate/skin region the wound sits on: a compact, solid, non-border object
    among SAM's masks or the holes of SAM's background masks. None if not found."""
    h, w = candidates_small[0][0].shape
    objects = []
    for m, _ in candidates_small:
        m = _largest_component(imaging.open_close(m, 2))
        if not _touches_border(m):
            objects.append(imaging.fill_holes(m))
        lab = imaging.label(imaging.fill_holes(m) & ~m)       # holes = objects on the background
        for k in range(1, lab.max() + 1):
            objects.append(imaging.fill_holes(lab == k))
    best, best_key = None, None
    for o in objects:
        f = o.mean()
        if not (CONTAINER_MIN_FRACTION < f < CONTAINER_MAX_FRACTION):
            continue
        solidity, aspect = shape_stats(o)
        if aspect > CONTAINER_MAX_ASPECT or solidity < CONTAINER_MIN_SOLIDITY:
            continue
        ys, xs = np.nonzero(o)
        off_centre = np.hypot(ys.mean() / h - 0.5, xs.mean() / w - 0.5)
        key = solidity - 0.5 * off_centre + 0.2 * min(f / 0.15, 1.0)
        if best_key is None or key > best_key:
            best, best_key = o, key
    return best


def _robust_quadratic_residual(depth_mm, sel, shape):
    """Height (mm, + towards the camera) relative to a robust quadratic surface
    fitted to depth samples in `sel`; tolerant of tilt and gently curved surfaces."""
    h, w = shape
    ys, xs = np.nonzero(sel)
    A = np.stack([np.ones_like(xs), xs, ys, xs * xs, ys * ys, xs * ys], axis=1).astype(np.float64)
    z = depth_mm[ys, xs].astype(np.float64)
    keep = np.ones(z.size, dtype=bool)
    coef = np.zeros(6)
    for _ in range(4):
        coef, *_ = np.linalg.lstsq(A[keep], z[keep], rcond=None)
        r = z - A @ coef
        mad = 1.4826 * np.median(np.abs(r[keep] - np.median(r[keep]))) + 1e-6
        keep = np.abs(r) < 2.5 * mad
    Y, X = np.mgrid[0:h, 0:w]
    full = np.stack([np.ones_like(X), X, Y, X * X, Y * Y, X * Y], axis=-1).astype(np.float64)
    return full @ coef - depth_mm


def locate_wound(rgb_small, depth_mm_small, valid_small, container):
    """Most salient compact region inside the container, or None."""
    h, w = container.shape
    size = float(np.sqrt(container.sum()))
    core = container
    for _ in range(max(2, int(0.08 * size))):                 # stay off the plate rim / edge step
        core = imaging.erode(core, 1)
    if core.sum() < 50:
        return None
    rgb = rgb_small.astype(np.float64)
    lum = rgb.mean(axis=2)
    chroma = rgb / np.maximum(lum[..., None], 1.0)
    colour = np.linalg.norm(chroma - np.median(chroma[core], axis=0), axis=2) * 100.0
    # Specular glare: bright, washed-out pixels shift chroma without being wound tissue.
    sat = (rgb.max(axis=2) - rgb.min(axis=2)) / np.maximum(rgb.max(axis=2), 1.0)
    glare = (lum > np.percentile(lum[core], 90)) & (sat < 0.7 * np.median(sat[core]))
    colour = np.where(imaging.dilate(glare, 1), 0.0, colour)
    # LiDAR relief: only well inside the container (the 256x192 depth map smears the
    # plate/table step over several mm) and only where it exceeds sensor noise.
    deep = core
    for _ in range(max(2, int(0.07 * size))):
        deep = imaging.erode(deep, 1)
    relief = np.zeros((h, w))
    sel = deep & valid_small
    if sel.sum() >= 50:
        r = np.abs(_robust_quadratic_residual(depth_mm_small, sel, (h, w)))
        relief = np.where(deep, np.clip(r - RELIEF_NOISE_MM, 0, None), 0.0)
        relief = relief / max(np.percentile(relief[deep], 95), RELIEF_FLOOR_MM)
    colour_n = colour / max(np.percentile(colour[core], 95), 1e-3)
    saliency = colour_n + RELIEF_WEIGHT * relief
    cy, cx = np.mean(np.nonzero(container), axis=1)
    Y, X = np.mgrid[0:h, 0:w]
    saliency = np.where(core, saliency * np.exp(-((Y - cy) ** 2 + (X - cx) ** 2) / (2 * (CENTRE_SIGMA * size) ** 2)), 0.0)
    cand = core & (saliency > max(np.percentile(saliency[core], SALIENCY_PERCENTILE), 0.6))
    cand = imaging.open_close(cand, 2)
    # A textured wound (granulation, slough islands) breaks into fragments at the
    # threshold; group fragments that are within BLOB_MERGE_PX of each other.
    groups = imaging.label(imaging.dilate(cand, BLOB_MERGE_PX))
    best, best_key = None, None
    for k in range(1, groups.max() + 1):
        frag = cand & (groups == k)
        if not frag.any():
            continue
        c = core & imaging.fill_holes(frag | imaging.erode(imaging.dilate(frag, BLOB_MERGE_PX), BLOB_MERGE_PX))
        f = c.sum() / container.sum()
        if not (BLOB_MIN_FRACTION <= f <= BLOB_MAX_FRACTION):
            continue
        solidity, aspect = shape_stats(c)
        if aspect > 3.5:                                      # scale bar, text, plate edge
            continue
        if colour_n[c].mean() < BLOB_MIN_COLOUR:
            continue
        key = float(saliency[c].sum()) * solidity
        if best_key is None or key > best_key:
            best, best_key = c, key
    return None if best is None else imaging.fill_holes(best)


def interior_point(m):
    """A point deep inside the mask (last survivor of repeated erosion)."""
    last = cur = m
    while cur.any():
        last, cur = cur, imaging.erode(cur, 1)
    ys, xs = np.nonzero(last)
    i = ys.size // 2
    return float(xs[i]), float(ys[i])


def negative_points(container, blob, n_max=4):
    """Points on the container surface well away from the blob (SAM negatives)."""
    size = float(np.sqrt(container.sum()))
    core = container
    for _ in range(max(2, int(0.08 * size))):
        core = imaging.erode(core, 1)
    away = core & ~imaging.dilate(blob, max(3, int(0.08 * size)))
    by, bx = np.mean(np.nonzero(blob), axis=1)
    ys, xs = np.nonzero(away)
    pts = []
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        proj = (xs - bx) * dx + (ys - by) * dy
        ok = proj > 0.25 * size
        if ok.any():
            i = np.argmax(np.where(ok, proj - 0.5 * np.abs((xs - bx) * dy + (ys - by) * dx), -np.inf))
            pts.append((float(xs[i]), float(ys[i])))
    return pts[:n_max]


def choose_by_blob(candidates, blob, container):
    """SAM mask with the best overlap with the located region, rejecting masks
    that are (most of) the container itself. Returns (mask, score, iou) or None."""
    best, best_key = None, None
    grown, grown_key = None, None
    csum, bsum = container.sum(), max(1, int(blob.sum()))
    for m, score in candidates:
        if m.shape != blob.shape:
            m = imaging.resample_nearest(m.astype(np.uint8), blob.shape[1], blob.shape[0]) > 0
        area = m.sum()
        if area == 0 or area > WOUND_MAX_CONTAINER_FRACTION * csum or _touches_border(m):
            continue
        if (m & container).sum() < 0.85 * area:               # spills off the plate
            continue
        inter = (m & blob).sum()
        iou = float(inter / max(1, (m | blob).sum()))
        key = iou + 0.05 * score
        if best_key is None or key > best_key:
            best, best_key = (m, score, iou), key
        # The locator region is a seed, often only the wound's centre (the centre prior
        # trims elongated wounds): also accept a mask that contains it and is not much larger.
        cover = inter / bsum
        if cover >= MIN_BLOB_COVER and area <= MAX_GROWTH * bsum:
            gkey = cover - 0.02 * area / bsum + 0.05 * score
            if grown_key is None or gkey > grown_key:
                grown, grown_key = (m, score, iou), gkey
    if best is not None and best[2] >= MIN_BLOB_IOU:
        return best
    return grown


def clean_mask(m, point_xy):
    m = imaging.open_close(m, 2)
    m = imaging.component_at(m, point_xy[0], point_xy[1], search_px=max(m.shape) // 8)
    return imaging.fill_holes(m)


def depth_fallback(points, valid, point_xy, min_recess_mm=1.2):
    """Recessed region at the prompt, relative to the surrounding surface.

    Used only when SAM is unavailable after retries. The reference surface is
    fitted to an annulus around the frame centre (where the capture reticle puts
    the wound). Returns None, so the step fails cleanly, unless the surroundings
    are flat and the recess is compact; noisy or non-planar scenes are refused
    rather than producing implausible numbers.
    """
    h, w = valid.shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot((xx - point_xy[0]) / w, (yy - point_xy[1]) / h)
    annulus = valid & (r > 0.15) & (r < 0.40)
    if annulus.sum() < 100:
        return None
    pts = points[annulus]
    n, d = geometry.fit_plane(pts)
    rmse = float(np.sqrt(np.mean((pts @ n - d) ** 2)))
    if rmse > FALLBACK_MAX_PLANE_RMSE_MM:
        return None
    height = points @ n - d
    recessed = valid & (height < -min_recess_mm) & (r < 0.40)
    m = clean_mask(recessed, point_xy)
    frac = m.sum() / (h * w)
    if not (MIN_AREA_FRACTION <= frac <= FALLBACK_MAX_FRACTION):
        return None
    return m


def overlay_jpeg(rgb_img, wound, ring):
    a = np.asarray(rgb_img).astype(np.float32).copy()
    a[ring] = a[ring] * 0.5 + np.array([255, 200, 0]) * 0.5
    a[wound] = a[wound] * 0.5 + np.array([255, 0, 0]) * 0.5
    a[imaging.boundary(wound)] = [255, 255, 255]
    from PIL import Image
    buf = io.BytesIO()
    Image.fromarray(a.astype(np.uint8)).save(buf, format="JPEG", quality=85)
    return buf.getvalue()
