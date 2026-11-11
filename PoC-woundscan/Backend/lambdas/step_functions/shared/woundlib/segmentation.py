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
MAX_AREA_FRACTION = 0.25     # a wound centred at ~20 cm fills well under a quarter of the frame
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


def sam_predict(jpeg_bytes, point_xy):
    """Call the SAM endpoint. Returns a list of (mask bool array, score)."""
    body = {
        "image": base64.b64encode(jpeg_bytes).decode("ascii"),
        "points": [[float(point_xy[0]), float(point_xy[1])]],
        "labels": [1],
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
