"""End-to-end run through the deployed API, exactly like the iOS app:

    POST /scans -> PUT 25 files to the presigned URLs -> poll /status -> GET /results

    python e2e_api.py BUNDLE_DIR [--api https://7vo1pzlg1f.execute-api.us-east-1.amazonaws.com]

BUNDLE_DIR holds frame_{1..5}_{rgb.jpg,depth.bin,confidence.bin,intrinsics.json,metadata.json},
e.g. made with `python synthetic.py OUT --preset ellipse-42x29x6`. Only needs `requests`-free stdlib.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

DEFAULT_API = "https://7vo1pzlg1f.execute-api.us-east-1.amazonaws.com"


def call(method, url, body=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(url, data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle")
    ap.add_argument("--api", default=DEFAULT_API)
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()

    t0 = time.time()
    st, body = call("POST", f"{a.api}/scans", {"session": {"device": "e2e_api.py", "bundle": os.path.basename(a.bundle)}})
    if st != 200:
        sys.exit(f"POST /scans -> {st}: {body[:300]}")
    resp = json.loads(body)
    scan_id, urls = resp["scanId"], resp["uploadUrls"]
    print(f"scanId {scan_id}: uploading {len(urls)} files")
    for key, url in urls.items():
        name = key.split("/")[-1]
        with open(os.path.join(a.bundle, name), "rb") as f:
            st, b = call("PUT", url, raw=f.read())
        if st != 200:
            sys.exit(f"PUT {name} -> {st}: {b[:300]}")
    print(f"uploaded in {time.time() - t0:.1f}s; polling status")

    last = None
    while time.time() - t0 < a.timeout:
        st, b = call("GET", f"{a.api}/scans/{scan_id}/status")
        status = json.loads(b).get("status") if st == 200 else f"HTTP {st}"
        if status != last:
            print(f"  {time.time() - t0:6.1f}s  {status}")
            last = status
        if status in ("COMPLETE", "FAILED"):
            break
        time.sleep(5)
    st, b = call("GET", f"{a.api}/scans/{scan_id}/results")
    print(f"GET /results -> {st}")
    res = json.loads(b)
    print(json.dumps({k: v for k, v in res.items() if k != "diagrams"}, indent=2)[:3000])
    if st == 200:
        for k, url in res["diagrams"].items():
            s2, d = call("GET", url)
            print(f"  {k}: HTTP {s2}, {len(d)} bytes")
    print(f"total {time.time() - t0:.1f}s")
    sys.exit(0 if st == 200 else 1)


if __name__ == "__main__":
    main()
