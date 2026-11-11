"""S3 helpers and the key layout shared by all pipeline steps.

Every step reads its inputs from S3 and writes its outputs to S3 (SOW 1.4);
only small JSON pointers travel through Step Functions.

Layout
------
assets bucket (event["bucket"]):
    scans/{scanId}/frames/frame_{1..5}_{rgb.jpg,depth.bin,confidence.bin,intrinsics.json,metadata.json}
    processed/{scanId}/measurements.json | diagram_top.svg | diagram_cross.png | narration.txt
state bucket (env STATE_BUCKET, falls back to the assets bucket):
    work/{scanId}/preprocess.npz, best_rgb.jpg, segment.npz, segment.json, geometry.npz, ...
"""

import io
import json
import os

import boto3
import numpy as np

_s3 = None


def s3():
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3")
    return _s3


class PipelineError(Exception):
    """A handled, user-meaningful failure. Its message is stored in DynamoDB `error`."""


def parse_event(event):
    scan_id = event.get("scanId")
    bucket = event.get("bucket")
    if not scan_id or not bucket:
        raise PipelineError("Workflow input must contain scanId and bucket")
    prefix = event.get("prefix") or f"scans/{scan_id}/frames/"
    state_bucket = os.environ.get("STATE_BUCKET") or bucket
    return scan_id, bucket, prefix, state_bucket


def work_key(scan_id, name):
    return f"work/{scan_id}/{name}"


def processed_key(scan_id, name):
    return f"processed/{scan_id}/{name}"


def get_bytes(bucket, key):
    try:
        return s3().get_object(Bucket=bucket, Key=key)["Body"].read()
    except s3().exceptions.NoSuchKey:
        raise PipelineError(f"Missing input s3://{bucket}/{key}")


def put_bytes(bucket, key, data, content_type="application/octet-stream"):
    s3().put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
    return key


def get_json(bucket, key):
    return json.loads(get_bytes(bucket, key).decode("utf-8"))


def put_json(bucket, key, obj):
    return put_bytes(bucket, key, json.dumps(obj, indent=2).encode("utf-8"), "application/json")


def put_text(bucket, key, text, content_type="text/plain; charset=utf-8"):
    return put_bytes(bucket, key, text.encode("utf-8"), content_type)


def get_npz(bucket, key):
    with np.load(io.BytesIO(get_bytes(bucket, key)), allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def put_npz(bucket, key, **arrays):
    buf = io.BytesIO()
    np.savez_compressed(buf, **arrays)
    return put_bytes(bucket, key, buf.getvalue())
