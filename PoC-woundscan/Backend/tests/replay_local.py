"""Replay captured scans through the pipeline steps locally (no Step Functions, no S3).

Usage:
    python replay_local.py RAW_DIR OUT_DIR [scanId ...]

RAW_DIR/<scanId>/frames/frame_{1..5}_* is the layout produced by
`aws s3 sync s3://<assets>/scans/<scanId>/ RAW_DIR/<scanId>/`.
S3 reads/writes are redirected to OUT_DIR/<bucket>/<key>. SAM is called on the
real endpoint when SAGEMAKER_ENDPOINT_NAME is set (AWS_PROFILE must allow
sagemaker:InvokeEndpoint); SAM candidates are cached in OUT_DIR/sam_cache so
re-runs are free and deterministic. NARRATE is skipped.
"""

import hashlib
import io
import json
import os
import shutil
import sys
import traceback

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lambdas", "step_functions", "shared"))

from woundlib import s3io, segmentation, steps  # noqa: E402

OUT = None


def _path(bucket, key):
    return os.path.join(OUT, bucket, *key.split("/"))


def get_bytes(bucket, key):
    p = _path(bucket, key)
    if not os.path.exists(p):
        raise s3io.PipelineError(f"Missing input s3://{bucket}/{key}")
    with open(p, "rb") as f:
        return f.read()


def put_bytes(bucket, key, data, content_type="application/octet-stream"):
    p = _path(bucket, key)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)
    return key


def get_json(bucket, key):
    return json.loads(get_bytes(bucket, key).decode("utf-8"))


def put_json(bucket, key, obj):
    return put_bytes(bucket, key, json.dumps(obj, indent=2, default=float).encode("utf-8"))


def put_text(bucket, key, text, content_type=None):
    return put_bytes(bucket, key, text.encode("utf-8"))


def get_npz(bucket, key):
    with np.load(io.BytesIO(get_bytes(bucket, key)), allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def put_npz(bucket, key, **arrays):
    buf = io.BytesIO()
    np.savez_compressed(buf, **arrays)
    return put_bytes(bucket, key, buf.getvalue())


_real_sam = segmentation.sam_predict


def cached_sam(jpeg_bytes, point_xy, *args, **kwargs):
    extra = json.dumps([args, kwargs], sort_keys=True, default=str)
    h = hashlib.sha1(jpeg_bytes + json.dumps([list(map(float, point_xy)), extra]).encode()).hexdigest()
    p = os.path.join(OUT, "sam_cache", h + ".npz")
    if os.path.exists(p):
        with np.load(p) as z:
            return [(z[f"m{i}"], float(z["scores"][i])) for i in range(len(z["scores"]))]
    res = _real_sam(jpeg_bytes, point_xy, *args, **kwargs)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    np.savez_compressed(p, scores=np.array([s for _, s in res]), **{f"m{i}": m for i, (m, _) in enumerate(res)})
    return res


def patch():
    for mod in (s3io, steps):
        for name in ("get_bytes", "put_bytes", "get_json", "put_json", "put_text", "get_npz", "put_npz"):
            if hasattr(mod, name):
                setattr(mod, name, globals()[name])
    segmentation.sam_predict = cached_sam


def run(raw_dir, scan_id):
    bucket, state = "assets", "state"
    os.environ["STATE_BUCKET"] = state
    src = os.path.join(raw_dir, scan_id, "frames")
    dst = _path(bucket, f"scans/{scan_id}/frames")
    if not os.path.isdir(dst):
        shutil.copytree(src, dst)
    ev = {"scanId": scan_id, "bucket": bucket, "prefix": f"scans/{scan_id}/frames/", "retryCount": 2}
    out = {"scanId": scan_id}
    try:
        if not (os.environ.get("REPLAY_REUSE_PREPROCESS") and os.path.exists(_path(state, f"work/{scan_id}/preprocess.npz"))):
            steps.preprocess(ev)
        out["segment"] = steps.segment(ev)
        out["measurements"] = steps.compute(ev)["measurements"]
        steps.generate_diagrams(ev)
        out["status"] = "COMPLETE"
    except s3io.PipelineError as e:
        out["status"], out["error"] = "FAILED", str(e)
    except Exception as e:
        out["status"], out["error"] = "ERROR", f"{type(e).__name__}: {e}"
        traceback.print_exc()
    return out


def main():
    global OUT
    raw_dir, OUT = sys.argv[1], sys.argv[2]
    ids = sys.argv[3:] or sorted(os.listdir(raw_dir))
    patch()
    results = []
    for sid in ids:
        r = run(raw_dir, sid)
        results.append(r)
        m = r.get("measurements") or {}
        print(f"{sid[:8]} {r['status']:8} L={m.get('length_mm')} W={m.get('width_mm')} "
              f"A={m.get('bed_area_cm2')} D={m.get('depth_mm')} {r.get('segment', {}).get('method', '')} "
              f"{r.get('error', '')[:110]}", flush=True)
    with open(os.path.join(OUT, "results.json"), "w") as f:
        json.dump(results, f, indent=2, default=float)


if __name__ == "__main__":
    main()
