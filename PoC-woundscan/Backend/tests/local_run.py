"""Run the five pipeline steps locally against a capture bundle directory.

S3 is replaced by a directory-backed fake, so no AWS access is needed except for
the optional real SAM endpoint / Bedrock narration.

    python local_run.py BUNDLE_DIR OUT_DIR [--sam fake|endpoint|none] [--narrate bedrock|template|skip]

`--sam fake` thresholds the red wound colour of synthetic bundles to stand in for SAM.
"""

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lambdas", "step_functions", "shared"))

import numpy as np  # noqa: E402

from woundlib import imaging, narration, s3io, segmentation, steps  # noqa: E402


class _NoSuchKey(Exception):
    pass


class FakeS3:
    """Minimal get_object/put_object over a local directory (bucket = sub-directory)."""

    class exceptions:
        NoSuchKey = _NoSuchKey

    def __init__(self, root):
        self.root = root

    def _path(self, bucket, key):
        return os.path.join(self.root, bucket, *key.split("/"))

    def get_object(self, Bucket, Key):
        p = self._path(Bucket, Key)
        if not os.path.exists(p):
            raise _NoSuchKey(Key)
        import io
        return {"Body": io.BytesIO(open(p, "rb").read())}

    def put_object(self, Bucket, Key, Body, ContentType=None):
        p = self._path(Bucket, Key)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(Body)


def fake_sam(jpeg_bytes, point_xy):
    img = np.asarray(imaging.load_rgb(jpeg_bytes)).astype(int)
    red = (img[..., 0] - img[..., 1] > 60) & (img[..., 0] < 200)
    return [(red, 0.95), (imaging.dilate(red, 3), 0.80)]


def run(bundle, out, sam="fake", narrate="template", scan_id="local-scan"):
    fake = FakeS3(out)
    s3io._s3 = fake
    os.environ["STATE_BUCKET"] = "state"
    # stage the bundle into the fake assets bucket
    for f in os.listdir(bundle):
        if f.startswith("frame_"):
            fake.put_object("assets", f"scans/{scan_id}/frames/{f}", open(os.path.join(bundle, f), "rb").read())
    if sam == "fake":
        segmentation.sam_predict = fake_sam
        os.environ["SAGEMAKER_ENDPOINT_NAME"] = "fake"
    elif sam == "none":
        os.environ.pop("SAGEMAKER_ENDPOINT_NAME", None)
        os.environ.pop("SAGEMAKER_ENDPOINT_ARN", None)
    if narrate == "template":
        narration.generate = lambda model_id, m: narration.template(m)
        os.environ.pop("BEDROCK_GUARDRAIL_ID", None)
    event = {"scanId": scan_id, "bucket": "assets", "prefix": f"scans/{scan_id}/frames/", "session": {},
             "retryCount": 2}
    timings = {}
    for name, fn in [("preprocess", steps.preprocess), ("segment", steps.segment), ("compute", steps.compute),
                     ("generate_diagrams", steps.generate_diagrams), ("narrate", steps.narrate)]:
        if name == "narrate" and narrate == "skip":
            continue
        t = time.time()
        res = fn(event)
        timings[name] = round(time.time() - t, 2)
        print(f"{name:18s} {timings[name]:6.2f}s  {json.dumps(res, default=str)[:160]}")
    m = json.load(open(os.path.join(out, "assets", "processed", scan_id, "measurements.json")))
    gt_path = os.path.join(bundle, "ground_truth.json")
    if os.path.exists(gt_path):
        gt = json.load(open(gt_path))["expected"]
        print(f"{'metric':22s} {'measured':>9s} {'truth':>9s} {'error':>8s}")
        for k, v in gt.items():
            err = m[k] - v
            print(f"{k:22s} {m[k]:9.2f} {v:9.2f} {err:+8.2f} ({100 * err / v:+.1f}%)")
    print("quality:", json.dumps(m["meta"]["quality"]))
    return m


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle")
    ap.add_argument("out")
    ap.add_argument("--sam", default="fake", choices=["fake", "endpoint", "none"])
    ap.add_argument("--narrate", default="template", choices=["bedrock", "template", "skip"])
    a = ap.parse_args()
    run(a.bundle, a.out, a.sam, a.narrate)
