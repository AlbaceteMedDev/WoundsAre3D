"""The five pipeline steps. Each reads its inputs from S3 and writes its outputs to S3.

Handlers return a small JSON summary that Step Functions stores under
`$.steps.<name>`; no image/depth data travels through the state machine.
"""

import io
import json
import logging
import time

import numpy as np

from . import diagrams, geometry, imaging, narration, segmentation
from .s3io import (PipelineError, get_bytes, get_json, get_npz, parse_event, processed_key,
                   put_bytes, put_json, put_npz, put_text, work_key)

log = logging.getLogger(__name__)
FRAME_COUNT = 5
DEPTH_MIN_M, DEPTH_MAX_M = 0.05, 3.0


def _frame_key(prefix, i, kind):
    return f"{prefix}frame_{i}_{kind}"


# ============================================================================ PREPROCESS

def preprocess(event):
    """Score the 5 frames for sharpness, pick the best one and register its depth
    map onto the RGB analysis grid."""
    scan_id, bucket, prefix, state = parse_event(event)
    t0 = time.time()
    scores, images = [], {}
    for i in range(1, FRAME_COUNT + 1):
        try:
            img = imaging.load_rgb(get_bytes(bucket, _frame_key(prefix, i, "rgb.jpg")))
        except PipelineError:
            scores.append({"frame": i, "missing": True})
            continue
        except Exception as e:
            scores.append({"frame": i, "error": f"unreadable rgb: {e}"[:120]})
            continue
        images[i] = img
        scores.append({"frame": i, "sharpness": round(imaging.sharpness(img), 2)})
    usable = [s for s in scores if "sharpness" in s]
    if not usable:
        raise PipelineError("No readable RGB frames in the capture bundle")

    # Depth quality per usable frame (fraction of valid samples in the centre).
    best, best_key = None, None
    for s in usable:
        i = s["frame"]
        try:
            K = get_json(bucket, _frame_key(prefix, i, "intrinsics.json"))
            W, H = images[i].size
            d, c = imaging.decode_depth(get_bytes(bucket, _frame_key(prefix, i, "depth.bin")),
                                        get_bytes(bucket, _frame_key(prefix, i, "confidence.bin")), W, H)
        except Exception as e:
            s["depth_error"] = str(e)[:120]
            continue
        h, w = d.shape
        centre = d[h // 4: 3 * h // 4, w // 4: 3 * w // 4]
        ok = np.isfinite(centre) & (centre > DEPTH_MIN_M) & (centre < DEPTH_MAX_M)
        s["depth_valid_centre"] = round(float(ok.mean()), 3)
        s["_data"] = (K, d, c)
    candidates = [s for s in usable if "_data" in s and s["depth_valid_centre"] >= 0.3]
    if not candidates:
        raise PipelineError("No frame has usable LiDAR depth in the centre of the image")
    max_sharp = max(s["sharpness"] for s in candidates) or 1.0
    for s in candidates:
        s["score"] = round(0.7 * s["sharpness"] / max_sharp + 0.3 * s["depth_valid_centre"], 4)
        key = s["score"]
        if best_key is None or key > best_key:
            best, best_key = s, key
    i = best["frame"]
    K, depth, conf = best["_data"]
    img = images[i]
    W, H = img.size

    valid = np.isfinite(depth) & (depth > DEPTH_MIN_M) & (depth < DEPTH_MAX_M)
    confident = valid & (conf >= 1)
    if confident.mean() > 0.5 * valid.mean():
        valid = confident                       # drop low-confidence samples when enough remain
    depth_f = imaging.median3(depth, valid)
    valid_f = np.isfinite(depth_f)
    depth_f, filled = imaging.fill_invalid(np.nan_to_num(depth_f), valid_f, iterations=96)

    Wa, Ha = imaging.analysis_size(W, H)
    reg_depth = imaging.resample_bilinear(depth_f, Wa, Ha)
    reg_valid = imaging.resample_nearest(valid_f, Wa, Ha)
    Ka = imaging.scale_intrinsics(K, K.get("width", W), K.get("height", H), Wa, Ha)

    small = img.resize((Wa, Ha), resample=3)
    buf = io.BytesIO()
    small.save(buf, format="JPEG", quality=92)
    put_bytes(state, work_key(scan_id, "best_rgb.jpg"), buf.getvalue(), "image/jpeg")
    meta = {}
    try:
        meta = get_json(bucket, _frame_key(prefix, i, "metadata.json"))
    except Exception:
        pass
    put_npz(state, work_key(scan_id, "preprocess.npz"),
            depth_m=reg_depth, valid=reg_valid,
            K=np.array([Ka["fx"], Ka["fy"], Ka["cx"], Ka["cy"]], dtype=np.float64))
    summary = {
        "bestFrame": i,
        "rgbSize": [W, H], "depthSize": [int(depth.shape[1]), int(depth.shape[0])],
        "analysisSize": [Wa, Ha],
        "depthValidFraction": round(float(valid.mean()), 3),
        "medianDepthM": round(float(np.median(depth[valid])), 3) if valid.any() else None,
        "orientation": meta.get("deviceOrientation"),
        "frames": [{k: v for k, v in s.items() if not k.startswith("_")} for s in scores],
        "seconds": round(time.time() - t0, 2),
    }
    put_json(state, work_key(scan_id, "preprocess.json"), summary)
    return {"bestFrame": i, "depthValidFraction": summary["depthValidFraction"]}


def _load_registered(state, scan_id):
    z = get_npz(state, work_key(scan_id, "preprocess.npz"))
    fx, fy, cx, cy = [float(v) for v in z["K"]]
    h, w = z["depth_m"].shape
    K = {"fx": fx, "fy": fy, "cx": cx, "cy": cy, "width": w, "height": h}
    points = imaging.backproject(z["depth_m"], K)
    return z["depth_m"], z["valid"].astype(bool), K, points


# ============================================================================ SEGMENT

def segment(event):
    """SAM ViT-B (centre-point prompt) -> wound mask; 20 mm peri-wound ring mask."""
    scan_id, bucket, prefix, state = parse_event(event)
    retry = int(event.get("retryCount", 0) or 0)
    t0 = time.time()
    jpeg = get_bytes(state, work_key(scan_id, "best_rgb.jpg"))
    img = imaging.load_rgb(jpeg)
    _, valid, K, points = _load_registered(state, scan_id)
    h, w = valid.shape
    prompt = (w / 2.0, h / 2.0)

    method, score, sam_error, wound = None, None, None, None
    if segmentation.endpoint_name():
        try:
            cands = segmentation.sam_predict(jpeg, prompt)
            chosen = segmentation.choose_sam_mask(cands, prompt, (h, w))
            if chosen is not None:
                wound = segmentation.clean_mask(chosen[0], prompt)
                score, method = chosen[1], "sam_vit_b"
            else:
                sam_error = "SAM returned no plausible mask for the centre prompt"
        except Exception as e:
            sam_error = f"{type(e).__name__}: {e}"[:300]
            log.warning("SAM call failed (retry %s): %s", retry, sam_error)
            # Let Step Functions retry transient endpoint errors (cold start, throttling);
            # only fall back to depth segmentation on the last attempt.
            if retry < 2:
                raise
    else:
        sam_error = "SAGEMAKER_ENDPOINT_NAME not configured"

    if wound is None or not wound.any():
        wound = segmentation.depth_fallback(points, valid, prompt)
        method = "depth_fallback"
        if wound is None:
            raise PipelineError(f"Segmentation failed: no wound region found at the image centre ({sam_error})")

    frac = float(wound.sum()) / (h * w)
    if not (segmentation.MIN_AREA_FRACTION <= frac <= segmentation.MAX_AREA_FRACTION):
        raise PipelineError(f"Segmentation produced an implausible wound size ({frac:.2%} of the frame)")

    ring = geometry.peri_wound_ring(points, np.ones_like(valid), wound)
    put_npz(state, work_key(scan_id, "segment.npz"), wound=np.packbits(wound), ring=np.packbits(ring),
            shape=np.array([h, w]))
    put_bytes(state, work_key(scan_id, "mask.png"), imaging.mask_to_png(wound), "image/png")
    put_bytes(state, work_key(scan_id, "ring.png"), imaging.mask_to_png(ring), "image/png")
    put_bytes(state, work_key(scan_id, "overlay.jpg"), segmentation.overlay_jpeg(img, wound, ring), "image/jpeg")
    info = {"method": method, "samScore": score, "samError": sam_error, "prompt": list(prompt),
            "woundFraction": round(frac, 5), "ringPixels": int(ring.sum()), "retryCount": retry,
            "seconds": round(time.time() - t0, 2)}
    put_json(state, work_key(scan_id, "segment.json"), info)
    return {"method": method, "samScore": score, "woundFraction": info["woundFraction"]}


def _load_masks(state, scan_id):
    z = get_npz(state, work_key(scan_id, "segment.npz"))
    h, w = [int(v) for v in z["shape"]]
    wound = np.unpackbits(z["wound"])[: h * w].reshape(h, w).astype(bool)
    ring = np.unpackbits(z["ring"])[: h * w].reshape(h, w).astype(bool)
    return wound, ring


# ============================================================================ COMPUTE

def compute(event):
    """3D projection, reference-plane fit, L/W/area/depth/peri-wound area."""
    scan_id, bucket, prefix, state = parse_event(event)
    t0 = time.time()
    _, valid, K, points = _load_registered(state, scan_id)
    wound, ring = _load_masks(state, scan_id)
    try:
        m, geom, quality = geometry.measure(points, valid, wound, ring, K)
    except ValueError as e:
        raise PipelineError(f"Measurement failed: {e}")
    for k in ("length_mm", "width_mm", "bed_area_cm2", "peri_wound_area_cm2"):
        if not m[k] > 0:
            raise PipelineError(f"Measurement {k} is zero; the wound region is too small or invalid")
    seg = {}
    try:
        seg = get_json(state, work_key(scan_id, "segment.json"))
    except Exception:
        pass
    doc = dict(m)
    doc["units"] = {"length_mm": "mm", "width_mm": "mm", "bed_area_cm2": "cm2", "depth_mm": "mm",
                    "peri_wound_area_cm2": "cm2"}
    doc["meta"] = {"scanId": scan_id, "segmentation": seg.get("method"), "samScore": seg.get("samScore"),
                   "periWoundRingMm": geometry.PERI_WOUND_RING_MM, "quality": quality,
                   "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    put_json(bucket, processed_key(scan_id, "measurements.json"), doc)
    put_npz(state, work_key(scan_id, "geometry.npz"), **{k: np.asarray(v) for k, v in geom.items()})
    log.info("measurements %s quality %s (%.1fs)", m, quality, time.time() - t0)
    return {"measurements": m}


# ============================================================================ GENERATE_DIAGRAMS

def generate_diagrams(event):
    scan_id, bucket, prefix, state = parse_event(event)
    geom = get_npz(state, work_key(scan_id, "geometry.npz"))
    m = get_json(bucket, processed_key(scan_id, "measurements.json"))
    svg = diagrams.top_view_svg(geom, m)
    png = diagrams.cross_section_png(geom, m)
    put_bytes(bucket, processed_key(scan_id, "diagram_top.svg"), svg.encode("utf-8"), "image/svg+xml")
    put_bytes(bucket, processed_key(scan_id, "diagram_cross.png"), png, "image/png")
    return {"diagramTop": processed_key(scan_id, "diagram_top.svg"),
            "diagramCross": processed_key(scan_id, "diagram_cross.png")}


# ============================================================================ NARRATE

def narrate(event):
    scan_id, bucket, prefix, state = parse_event(event)
    m = get_json(bucket, processed_key(scan_id, "measurements.json"))
    text, info = narration.narrate(m)
    put_text(bucket, processed_key(scan_id, "narration.txt"), text)
    put_json(state, work_key(scan_id, "narrate.json"), info)
    return {"source": info["source"], "model": info["model"], "words": len(text.split())}


def run_handler(fn, event):
    """Common wrapper: log, and turn PipelineError into a clean Step Functions error."""
    logging.getLogger().setLevel(logging.INFO)
    log.info("event %s", json.dumps({k: event.get(k) for k in ("scanId", "bucket", "prefix", "retryCount")}))
    return fn(event)
