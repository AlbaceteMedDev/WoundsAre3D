"""Download real-wound photographs with segmentation ground truth, check every
file against the publisher's own checksum, and lay them out for testing.

By default this fetches the two sets published under CC BY 4.0
(docs/wound-reference-images.md, section 5): CO2Wounds v1, which a company may
use with credit, and LUTSeg, for internal testing until its authors confirm
that licence in writing - most of its photographs look to come from a later
collection whose current release is non-commercial (LICENSES.md and each row's
note say which). Non-commercial datasets need --noncommercial and land apart,
under OUT/noncommercial/: their licences allow research use only, so clear
internal benchmarking with legal first, and never train the product on them or
show them in marketing. Patient images do not belong in any repository, so OUT
may not lie inside a git work tree.

    python scripts/fetch_wound_segmentation_data.py --out ~/woundscan-data/real-wounds
    python scripts/fetch_wound_segmentation_data.py --out DIR --noncommercial fuseg woundseg

For each dataset it writes
    raw/<dataset>/             the files as published, each one verified
    images/<dataset>/<id>.*    each photograph, byte for byte as published, its
                               suffix naming its format (.jpg for JPEG data:
                               CO2Wounds v1 publishes its JPEGs as .png)
    masks/<dataset>/<id>.png   its wound mask redrawn at the same size as 0
                               background and 255 wound (LICENSES.md says how)
    tissue/<dataset>/<id>.png  tissue classes as published, where the dataset has them
and, over all of them, manifest.csv - one row per photograph: source, licence,
size, split, patient, wound fraction, what its mask covers, the photograph it
repeats if any, and notes - and LICENSES.md, each dataset's licence and credit.
Re-running skips files already downloaded and verified; it stops if OUT holds
a dataset it was not asked for, rather than leave that one out of the manifest.
evaluate_segmentation.py scores a model on the result.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import http.client
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

AGENT = "woundscan-dataset-fetch/1.0"
LUTSEG_CLASSES = {
    0: "background",
    1: "epithelial",
    2: "slough",
    3: "granulation",
    4: "necrotic",
    5: "other",
    255: "ignore",
}
SUFFIXES = {"JPEG": (".jpg", ".jpeg"), "MPO": (".jpg", ".jpeg"), "PNG": (".png",)}
Row = dict[str, Any]


# ---------------------------------------------------------------- download --
def get(url: str, timeout: float = 120.0) -> tuple[bytes, Any]:
    """The body and headers at url, trying again after what may pass: server
    errors, rate limits, timeouts and connections cut mid-transfer."""
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    for attempt in range(4):
        wait = 2 ** (attempt + 1)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), r.headers
        except urllib.error.HTTPError as e:
            if (e.code < 500 and e.code not in (408, 429)) or attempt == 3:
                raise  # a refusal will not change on retry
            after = str((e.headers or {}).get("Retry-After") or "")
            if after.isdigit():
                wait = min(int(after), 120)
        except (OSError, http.client.HTTPException):  # timeouts, resets, truncated bodies
            if attempt == 3:
                raise
        time.sleep(wait)
    raise AssertionError("unreachable")


def outside_git(path: Path) -> Path:
    """path resolved, stopping the run if it lies inside a git work tree (this
    repository's or any other), where patient images could be committed."""
    p = path.expanduser().resolve()
    for d in (p, *p.parents):
        if (d / ".git").exists():
            sys.exit(f"{p} is inside the git work tree at {d}: keep patient images out of it")
    return p


def check(data: bytes, want: dict[str, Any]) -> bool:
    """True if data has the size and hash the publisher lists."""
    if "size" in want and len(data) != want["size"]:
        return False
    if "sha256" in want:
        return hashlib.sha256(data).hexdigest() == want["sha256"]
    if "git_sha1" in want:  # a Git blob: sha1 of "blob <size>", a zero byte, then the content
        return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest() == want["git_sha1"]
    raise ValueError(f"no checksum to verify against: {want}")


def fetch_all(jobs: list[tuple[str, Path, dict[str, Any]]], name: str) -> None:
    """Download each url to its path unless a verified copy is there."""
    new = 0
    for i, (url, dest, want) in enumerate(jobs, 1):
        if not (dest.exists() and check(dest.read_bytes(), want)):
            data, _ = get(url)
            if not check(data, want):
                raise RuntimeError(f"{url}: size or checksum differs from the publisher's")
            dest.parent.mkdir(parents=True, exist_ok=True)
            part = dest.with_name(dest.name + ".part")
            part.write_bytes(data)
            part.replace(dest)
            new += 1
        if i % 50 == 0 or i == len(jobs):
            print(f"  {name}: {i}/{len(jobs)} files verified ({new} downloaded)", flush=True)


def inside(root: Path, rel: str) -> Path:
    """root/rel, refusing a path that would leave root."""
    dest = (root / rel).resolve()
    if root.resolve() not in dest.parents:
        raise RuntimeError(f"{rel}: path leaves {root}")
    return dest


def mendeley(dataset: str, version: int, raw: Path) -> None:
    """A Mendeley Data record's files, from its "Download All" zip, each placed
    at its folder path and checked against the SHA-256 the publisher lists."""
    api = f"https://data.mendeley.com/public-api/datasets/{dataset}"
    folders = {f["id"]: f for f in json.loads(get(f"{api}/folders/{version}")[0])}

    def path(fid: str) -> Path:
        f = folders[fid]
        return (path(f["parent_id"]) if f.get("parent_id") in folders else Path()) / f["name"]

    want: dict[tuple[str, str], list[Path]] = {}  # (name, sha256) -> every place it is listed
    for fid in folders:
        for f in json.loads(get(f"{api}/files?folder_id={fid}&version={version}")[0]):
            key = (f["filename"], f["content_details"]["sha256_hash"])
            want.setdefault(key, []).append(inside(raw, str(path(fid) / f["filename"])))
    if all(
        p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() == sha
        for (_, sha), ps in want.items()
        for p in ps
    ):
        print(f"  {dataset} v{version}: {len(want)} files already verified", flush=True)
        return
    data, _ = get(f"https://data.mendeley.com/public-api/zip/{dataset}/download/{version}", 900)
    seen = set()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            body = z.read(info)
            key = (Path(info.filename).name, hashlib.sha256(body).hexdigest())
            if key not in want:
                raise RuntimeError(f"{info.filename}: not a file the publisher lists, or altered")
            for dest in want[key]:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(body)
            seen.add(key)
    if seen != set(want):
        raise RuntimeError(
            f"{dataset} v{version}: {len(set(want) - seen)} listed files not in the zip"
        )
    print(f"  {dataset} v{version}: {len(seen)} files downloaded and verified", flush=True)


def huggingface(repo: str, revision: str, raw: Path) -> None:
    """Every file of a Hugging Face dataset at a pinned revision, verified by
    its LFS SHA-256 or Git blob hash."""
    url: str | None = f"https://huggingface.co/api/datasets/{repo}/tree/{revision}?recursive=true"
    files: list[dict[str, Any]] = []
    while url:
        data, headers = get(url)
        files += [e for e in json.loads(data) if e["type"] == "file"]
        nxt = re.search(r'<([^>]+)>;\s*rel="next"', headers.get("Link") or "")
        url = nxt.group(1) if nxt else None
    fetch_all(
        [
            (
                f"https://huggingface.co/datasets/{repo}/resolve/{revision}/{e['path']}",
                inside(raw, e["path"]),
                (
                    {"sha256": e["lfs"]["oid"], "size": e["lfs"]["size"]}
                    if e.get("lfs")
                    else {"git_sha1": e["oid"], "size": e["size"]}
                ),
            )
            for e in files
        ],
        repo,
    )


def github(repo: str, commit: str, prefix: str, raw: Path) -> None:
    """Every file under prefix in a GitHub repository at a pinned commit,
    verified by its Git blob hash. The file list comes from the GitHub API or,
    where that is refused, from a clone that fetches no file contents."""
    try:
        data, _ = get(f"https://api.github.com/repos/{repo}/git/trees/{commit}?recursive=1")
        tree = json.loads(data)
        if tree.get("truncated"):
            raise RuntimeError(f"{repo}: the GitHub API truncated the file list")
        blobs = [(e["path"], e["sha"]) for e in tree["tree"] if e["type"] == "blob"]
    except urllib.error.HTTPError:
        with tempfile.TemporaryDirectory() as tmp:
            git = ["git", "-C", tmp]
            subprocess.run(["git", "init", "-q", tmp], check=True)
            subprocess.run(
                [
                    *git,
                    "fetch",
                    "-q",
                    "--depth",
                    "1",
                    "--filter=blob:none",
                    f"https://github.com/{repo}.git",
                    commit,
                ],
                check=True,
            )
            listing = subprocess.run(
                [*git, "ls-tree", "-r", "-z", commit], check=True, capture_output=True, text=True
            ).stdout
        blobs = [
            (entry.split("\t", 1)[1], entry.split()[2])
            for entry in listing.split("\0")
            if entry and entry.split()[1] == "blob"
        ]
    jobs = [
        (
            f"https://raw.githubusercontent.com/{repo}/{commit}/{urllib.parse.quote(p)}",
            inside(raw, p[len(prefix) :]),
            {"git_sha1": sha},
        )
        for p, sha in blobs
        if p.startswith(prefix)
    ]
    if not jobs:
        raise RuntimeError(f"{repo}@{commit}: nothing under {prefix}")
    fetch_all(jobs, repo)


# ------------------------------------------------------------------- masks --
# palette_greys, inside_out and plane are the same in evaluate_segmentation.py.
def palette_greys(im: Image.Image) -> np.ndarray | None:
    """A palette image's grey level for each index, where every colour in its
    palette is a grey: how Pillow's quantize() and convert(), and PNG
    optimisers, store a grey mask, in whatever order. None for any other image,
    and for a palette with a colour in it, whose indices are labels with 0 the
    background. The whole palette decides, not only the colours in use, so an
    empty label mask is read by the same rule as a full one."""
    if im.mode not in ("P", "PA"):
        return None
    pal = np.asarray(im.getpalette() or [], np.uint8).reshape(-1, 3)
    idx = np.asarray(im)
    idx = idx if idx.ndim == 2 else idx[..., 0]
    if not len(pal) or int(idx.max()) >= len(pal) or (pal != pal[:, :1]).any():
        return None
    return pal[:, 0]


def inside_out(im: Image.Image) -> bool:
    """Whether a palette image of labels has a colour at index 0 while black is
    another index in use: how Pillow's quantize() and ADAPTIVE palette store a
    coloured wound on black, which read by its indices would be inside out."""
    if im.mode not in ("P", "PA") or palette_greys(im) is not None:
        return False
    pal = np.asarray(im.getpalette() or [], np.uint8).reshape(-1, 3)
    if not len(pal) or not pal[0].any():
        return False
    idx = np.asarray(im)
    used = np.unique(idx if idx.ndim == 2 else idx[..., 0])
    used = used[(used > 0) & (used < len(pal))]
    return bool((pal[used].max(axis=1) == 0).any())


def plane(im: Image.Image) -> np.ndarray:
    """A mask image as one 2-D array, 0 the background: a palette of greys by
    its grey levels, one with colours by its indices (labels); otherwise its
    brightest colour channel, transparent pixels counting as background - or
    the alpha channel itself, where the colour is one flat value and only the
    alpha varies. An opaque black image is an empty mask, not a full one."""
    a = np.asarray(im)
    grey = palette_greys(im)
    if grey is not None:
        a = grey[a] if a.ndim == 2 else np.stack([grey[a[..., 0]], a[..., 1]], axis=2)
    if a.ndim == 2:
        return a
    if im.mode in ("LA", "La", "PA", "RGBA", "RGBa"):
        colour, alpha = a[..., :-1].max(axis=2), a[..., -1]
        if colour.min() == colour.max() and alpha.min() != alpha.max():
            return alpha  # one flat colour: the mask is in the alpha channel
        return np.where(alpha > 0, colour, 0)
    return a.max(axis=2)


def binary(path: Path) -> np.ndarray:
    """A published mask as a boolean array: wound where it is at or over half
    its scale (1, 255, or a 16-bit file's own top value), a palette of greys
    read by its grey levels; or, in a palette with colours in it, wherever the
    index is not 0. A mask that was resized carries grey levels along its edge
    (CO2Wounds v1: under 0.25 % of pixels). A file with over 1 % of pixels in
    mid-grey is not a mask, nor is a palette image with over 8 labels or one
    that inside_out() flags: each is refused."""
    im = Image.open(path)
    a = plane(im)
    if im.mode in ("P", "PA") and palette_greys(im) is None:  # labels: 0 is background
        if inside_out(im) or len(np.unique(a)) > 8:
            raise RuntimeError(f"{path}: a palette image, but not one of mask labels")
        return a != 0
    top = float(a.max())  # some masks store 0 and 1; a 16-bit one may run to 65535
    a = a.astype(np.float32) / (1.0 if top <= 1 else 255.0 if top <= 255 else top)
    if ((a > 0.12) & (a < 0.88)).mean() > 0.01:
        raise RuntimeError(f"{path}: too many mid-grey pixels for a binary mask")
    return a >= 0.5


def save_mask(mask: np.ndarray, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.where(mask, 255, 0).astype(np.uint8)).save(dest, optimize=True)


def pair(out: Path, name: str, stem: str, image: Path, mask_file: Path, **extra: Any) -> Row:
    """Copy a photograph, write its normalised mask, and return its row."""
    mask = binary(mask_file)
    with Image.open(image) as im:
        size, kind = im.size, im.format
    if size != mask.shape[::-1]:
        raise RuntimeError(f"{name} {stem}: photograph and mask differ in size")
    # The copy's suffix names what it holds: CO2Wounds v1 publishes JPEG data
    # under .png names, which readers that go by the suffix refuse.
    published = image.suffix.lower()
    real = SUFFIXES.get(kind or "", (published,))
    dest = out / "images" / name / f"{stem}{published if published in real else real[0]}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(image, dest)
    if published not in real:  # an earlier run's copy, under the published name
        dest.with_name(f"{stem}{published}").unlink(missing_ok=True)
    save_mask(mask, out / "masks" / name / f"{stem}.png")
    return dict(
        id=stem,
        image=f"images/{name}/{dest.name}",
        mask=f"masks/{name}/{stem}.png",
        split="",
        patient="",
        **extra,
    )


def enclose(boxes: list[list[float]]) -> list[float]:
    return [
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    ]


def box_iou(a: list[float], b: list[float]) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


# ---------------------------------------------------------------- datasets --
def co2wounds_v1(out: Path, raw: Path) -> list[Row]:
    """Photographs in JPEGImages/ (JPEG data under .png names), each padded
    to 640 x 640 with black bars; binary masks in Mask/; YOLO boxes in labels/
    for the wound and the calibration card in frame. Which box class is the
    wound is read from the masks. The card's size is not published, so the
    boxes give no millimetre scale."""
    names = sorted(
        (p.name for p in (raw / "JPEGImages").glob("*.png")), key=lambda n: int(Path(n).stem)
    )
    if len(names) != 164:
        raise RuntimeError(f"CO2Wounds v1: expected 164 photographs, found {len(names)}")
    rows, votes = [], {0: 0, 1: 0}
    for name in names:
        stem = Path(name).stem
        r = pair(out, "co2wounds-v1", stem, raw / "JPEGImages" / name, raw / "Mask" / name)
        h, w = np.asarray(Image.open(out / r["mask"])).shape
        found: dict[int, list[list[float]]] = {}
        for line in (raw / "labels" / f"{stem}.txt").read_text().split("\n"):
            if line.strip():
                c, cx, cy, bw, bh = (float(v) for v in line.split())
                found.setdefault(int(c), []).append(
                    [(cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h]
                )
        ys, xs = np.nonzero(np.asarray(Image.open(out / r["mask"])))
        if len(xs) and len(found) == 2:  # the class whose boxes fit the mask is the wound
            mb = [xs.min(), ys.min(), xs.max() + 1, ys.max() + 1]
            votes[max(found, key=lambda c: box_iou(enclose(found[c]), mb))] += 1
        r["boxes"] = found
        rows.append(r)
    wound = max(votes, key=lambda c: votes[c])
    if votes[wound] < 0.9 * sum(votes.values()):
        raise RuntimeError(f"CO2Wounds v1: box classes do not separate wound and card: {votes}")
    for r in rows:
        b = r.pop("boxes")
        r["wound_box_px"] = json.dumps([[round(v, 1) for v in x] for x in b.get(wound, [])])
        r["marker_box_px"] = json.dumps([[round(v, 1) for v in x] for x in b.get(1 - wound, [])])
    print(
        f"  CO2Wounds v1: YOLO class {wound} is the wound, {1 - wound} the calibration card "
        f"({votes[wound]} of {sum(votes.values())} images agree)"
    )
    return rows


def lutseg(out: Path, raw: Path) -> list[Row]:
    """Photographs by patient and visit, binary wound masks and six-class
    tissue masks, paired in metadata.jsonl."""
    rows = []
    for line in (raw / "metadata.jsonl").read_text().splitlines():
        m = json.loads(line)
        r = pair(
            out,
            "lutseg",
            m["image_id"],
            raw / m["image_file_name"],
            raw / m["wound_mask_file_name"],
            tissue=f"tissue/lutseg/{m['image_id']}.png",
        )
        tissue = np.asarray(Image.open(raw / m["mask_file_name"]))
        if tissue.shape != np.asarray(Image.open(out / r["mask"])).shape:
            raise RuntimeError(f"LUTSeg {m['image_id']}: tissue mask and photograph differ in size")
        if not set(np.unique(tissue).tolist()) <= set(LUTSEG_CLASSES):
            raise RuntimeError(f"LUTSeg {m['image_id']}: unknown tissue class")
        (out / r["tissue"]).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(raw / m["mask_file_name"], out / r["tissue"])
        r.update(split=m["split"], patient=m["patient_id"])
        rows.append(r)
    return rows


def fuseg(out: Path, raw: Path) -> list[Row]:
    """train/ and validation/, each with images/NNNN.png and labels/NNNN.png;
    the test photographs have no masks and are left out."""
    rows = []
    for split in ("train", "validation"):
        for image in sorted((raw / split / "images").glob("*.png")):
            mask = raw / split / "labels" / image.name
            if not mask.exists():
                raise RuntimeError(f"FUSeg {split}/{image.name}: no mask")
            r = pair(out, "fuseg", image.stem, image, mask)
            r["split"] = split
            rows.append(r)
    return rows


def woundseg(out: Path, raw: Path) -> list[Row]:
    """One zip holding sample/ (photographs) and mask/ folders, paired by file
    name. Its layout is not documented: the run stops if the two do not pair
    one to one."""
    unpacked = raw / "unpacked"
    if not unpacked.exists():  # unpack beside it, then rename: a half-done unpack is never used
        part = raw / "unpacked.part"
        shutil.rmtree(part, ignore_errors=True)
        with zipfile.ZipFile(raw / "wseg_dataset.zip") as z:
            for info in z.infolist():
                if not info.is_dir():
                    dest = inside(part, info.filename)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(z.read(info))
        part.rename(unpacked)
    files = [p for p in unpacked.rglob("*") if p.is_file() and not p.name.startswith(".")]
    sample_files = [p for p in files if p.parent.name == "sample"]
    mask_files = [p for p in files if p.parent.name == "mask"]
    samples = {p.stem: p for p in sample_files}
    masks = {p.stem: p for p in mask_files}
    if (
        not samples
        or samples.keys() != masks.keys()
        or len(samples) != len(sample_files)  # a name used twice, in different folders
        or len(masks) != len(mask_files)
    ):
        raise RuntimeError(
            f"WoundSeg: {len(sample_files)} photographs and {len(mask_files)} masks do not "
            "pair one to one by file name; inspect raw/woundseg/unpacked/"
        )
    return [pair(out, "woundseg", stem, samples[stem], masks[stem]) for stem in sorted(samples)]


def co2wounds_v2(out: Path, raw: Path) -> list[Row]:
    """imgs/IMG<n>.jpg|jpeg|png and masks/IMG<n>.png for the 607 labelled
    photographs; split/train/ and split/val/ say which split each is in."""
    split = {p.stem: s for s in ("train", "val") for p in (raw / "split" / s).iterdir()}
    images = {p.stem: p for p in (raw / "imgs").iterdir()}
    rows = []
    for mask in sorted((raw / "masks").glob("*.png")):
        r = pair(out, "co2wounds-v2", mask.stem, images[mask.stem], mask)
        r["split"] = split.get(mask.stem, "")
        rows.append(r)
    return rows


def lutseg_note(r: Row, fetched: set[str]) -> str:
    if "co2wounds-v1" not in fetched:
        return "fetch co2wounds-v1 too, to see whether this photograph is in its CC BY 4.0 release"
    if r["duplicate_of"].startswith("co2wounds-v1/"):
        return (
            f"photograph also in CO2Wounds v1 (CC BY 4.0) as {r['duplicate_of']}: use that row "
            "for commercial work; this row's masks are LUTSeg's own"
        )
    return (
        "not in CO2Wounds v1: probably from the later collection, whose current release is "
        "non-commercial; confirm the CC BY 4.0 grant with the authors before commercial use"
    )


DATASETS: dict[str, dict[str, Any]] = {
    "co2wounds-v1": {
        "fetch": lambda raw: mendeley("nkw5gx57hw", 1, raw),
        "layout": co2wounds_v1,
        "group": "usable",
        "licence": "CC BY 4.0",
        "licence_url": "https://creativecommons.org/licenses/by/4.0/",
        "source": "https://data.mendeley.com/datasets/nkw5gx57hw/1",
        "contents": "164 smartphone photographs of chronic leprosy ulcers from 69 consenting "
        "patients, Colombia, Nov 2021 - Jun 2022, padded to 640 x 640 with black bars, "
        "with binary wound masks and YOLO boxes for the wound and a calibration card "
        "(whose physical size is not published)",
        "attribution": "Monroy B, Sanchez K, Arguello P, Estupiñán J, Bacca J, Correa CV, Valencia L, "
        "Castillo JC, Mieles O, Arguello Fuentes H, Castillo S, Rojas-Morales F. "
        "CO2Wounds, version 1. Mendeley Data, 2022. doi:10.17632/nkw5gx57hw.1. "
        "Paper: Comput Biol Med 2023;165:107335, doi:10.1016/j.compbiomed.2023.107335.",
    },
    "lutseg": {
        "fetch": lambda raw: huggingface(
            "ksanchez84/LUTSeg", "e5115d4b2e5ecfc727f530deca9f3b0d032fb4bb", raw
        ),
        "layout": lutseg,
        "note": lutseg_note,
        "group": "confirm-first",
        "licence": "CC BY 4.0",
        "licence_url": "https://creativecommons.org/licenses/by/4.0/",
        "source": "https://huggingface.co/datasets/ksanchez84/LUTSeg "
        "(revision e5115d4b2e5ecfc727f530deca9f3b0d032fb4bb)",
        "contents": "141 photographs of leprosy-related ulcers from 39 patients over 21 months, "
        "with binary wound masks and six-class tissue masks (0 background, 1 epithelial, "
        "2 slough, 3 granulation, 4 necrotic, 5 other, 255 ignore); a 46-image subset "
        "outlined by five clinicians separately is in raw/lutseg/gold_standard/. Only 32 "
        "of the photographs are in CO2Wounds v1, whose licence LUTSeg says it inherits; "
        "the rest date from the later collection (see each row's note)",
        "attribution": "Sanchez K, Hinojosa C, Ávila Álvarez AA, Riano-Rojas AC, Romero Pinzon DH, "
        "Páez Figueroa JC, Llinás Tono M, Ghanem B. LUTSeg: A Longitudinal Multi-Expert Dataset "
        "for Ulcer Tissue Segmentation. Eleventh ISIC Skin Image Analysis Workshop @ MICCAI 2026. "
        "arXiv:2608.25866. https://huggingface.co/datasets/ksanchez84/LUTSeg",
    },
    "fuseg": {
        "fetch": lambda raw: github(
            "uwm-bigdata/wound-segmentation",
            "42a272dfe0679f20675e826385925cb7562934b6",
            "data/Foot Ulcer Segmentation Challenge/",
            raw,
        ),
        "layout": fuseg,
        "group": "noncommercial",
        "licence": "CC BY-NC (version not stated)",
        "licence_url": "https://raw.githubusercontent.com/uwm-bigdata/wound-segmentation/"
        "42a272dfe0679f20675e826385925cb7562934b6/data/Foot%20Ulcer%20Segmentation"
        "%20Challenge/FootUlcerSegmentationChallenge2021.pdf (data usage agreement)",
        "source": "https://github.com/uwm-bigdata/wound-segmentation, commit "
        "42a272dfe0679f20675e826385925cb7562934b6, data/Foot Ulcer Segmentation Challenge",
        "contents": "1,010 foot-ulcer photographs with wound masks (810 train, 200 validation; the "
        "200 test photographs have none and are left out), AZH Wound and Vascular "
        "Center; 24 masks are empty, and 7 photographs are in both train and validation",
        "attribution": "Wang C, et al. Fully automatic wound segmentation with deep convolutional "
        "neural networks. Sci Rep 2020;10:21897, doi:10.1038/s41598-020-78799-w. "
        "Foot Ulcer Segmentation Challenge, MICCAI 2021.",
    },
    "woundseg": {
        "fetch": lambda raw: huggingface(
            "subbareddyoota/wseg_dataset", "bdcc1e1cef607bfd7a4f98fc28f31a638a0e0ca9", raw
        ),
        "layout": woundseg,
        "mask_target": "wound and peri-wound skin",
        "group": "noncommercial",
        "licence": "CC BY-NC 4.0",
        "licence_url": "https://creativecommons.org/licenses/by-nc/4.0/",
        "source": "https://huggingface.co/datasets/subbareddyoota/wseg_dataset "
        "(revision bdcc1e1cef607bfd7a4f98fc28f31a638a0e0ca9)",
        "contents": "2,686 photographs of eight wound types, 224-331 px, whose masks include the "
        "peri-wound skin, so they are not comparable with wound-bed masks",
        "attribution": "Oota SR, et al. WSNet: Towards an Effective Method for Wound Image "
        "Segmentation. WACV 2023, pp. 3234-3243.",
    },
    "co2wounds-v2": {
        "fetch": lambda raw: mendeley("s2w7rjwz49", 2, raw),
        "layout": co2wounds_v2,
        "group": "noncommercial",
        "licence": "CC BY-NC 3.0 (Mendeley version 2; the paper says CC BY-NC-ND)",
        "licence_url": "https://creativecommons.org/licenses/by-nc/3.0/",
        "source": "https://data.mendeley.com/datasets/s2w7rjwz49/2",
        "contents": "764 photographs of leprosy ulcers from 96 patients, Nov 2021 - Aug 2023, with "
        "wound masks for 607 (485 train, 122 validation; the 157 test photographs have "
        "none); 24 groups of byte-identical photographs",
        "attribution": "Sanchez K, et al. CO2Wounds-V2: Extended Chronic Wounds Dataset From Leprosy "
        "Patients. ICIP 2024, pp. 69-75. Mendeley Data, doi:10.17632/s2w7rjwz49.2.",
    },
}


# ---------------------------------------------------------------- manifest --
def fingerprint(path: Path) -> tuple[tuple[int, int], np.ndarray, np.ndarray]:
    """Size and two normalised grey thumbnails of a photograph, after cropping
    away the black bars a dataset may pad it to a square with (CO2Wounds v1
    does)."""
    im = Image.open(path).convert("L")
    a = np.asarray(im)
    cols, lines = np.nonzero(a.max(axis=0) > 8)[0], np.nonzero(a.max(axis=1) > 8)[0]
    if len(cols) and len(lines):
        im = im.crop((cols[0], lines[0], cols[-1] + 1, lines[-1] + 1))

    def thumb(n: int) -> np.ndarray:
        t = np.asarray(im.resize((n, n), Image.BILINEAR), np.float32)
        t -= t.mean()
        return (t / (np.linalg.norm(t) + 1e-9)).astype(np.float32)

    return im.size, thumb(24), thumb(96)


def mark_repeats(rows: list[Row], earlier: list[Row]) -> None:
    """Flag a photograph published twice - byte for byte, or by another dataset
    resized, re-encoded, padded or turned by quarter turns - so it is not
    tested twice. The copy met first keeps it, counting `earlier` rows (an
    earlier fetch) first; every other copy names that first one in
    duplicate_of, with the quarter turns that bring it onto the first."""
    first: dict[str, tuple[str, int]] = {}
    for r in earlier:  # an earlier row may itself repeat another: point past it
        turns = int(r.get("duplicate_turns") or 0) if r["duplicate_of"] else 0
        first.setdefault(r["image_sha256"], (r["duplicate_of"] or r["key"], turns))
    for r in rows:
        if r["image_sha256"] in first:
            key, turns = first[r["image_sha256"]]
            r.update(duplicate_of=key, duplicate_turns=turns)
        else:
            first[r["image_sha256"]] = (r["key"], 0)
    fresh = [r for r in earlier + rows if not r["duplicate_of"]]
    prints = {r["key"]: fingerprint(r["path"]) for r in fresh}
    names = list(dict.fromkeys(r["dataset"] for r in fresh))
    for j, nb in enumerate(names):
        b_rows = [r for r in rows if r["dataset"] == nb and not r["duplicate_of"]]
        for na in names[:j]:
            a_rows = [r for r in fresh if r["dataset"] == na and not r["duplicate_of"]]
            if not a_rows or not b_rows:
                continue
            sa = np.stack([prints[r["key"]][1].ravel() for r in a_rows])
            for k in range(4):
                sb = np.stack([np.rot90(prints[r["key"]][1], k).ravel() for r in b_rows])
                for ia, ib in zip(*np.nonzero(sa @ sb.T >= 0.95), strict=True):
                    a, b = a_rows[ia], b_rows[ib]
                    (wa, ha), _, fine_a = prints[a["key"]]
                    (wb, hb), _, fine_b = prints[b["key"]]
                    wb, hb = (hb, wb) if k % 2 else (wb, hb)
                    if (
                        not b["duplicate_of"]
                        and abs(wa / ha - wb / hb) <= 0.03
                        and float((fine_a * np.rot90(fine_b, k)).sum()) >= 0.97
                    ):
                        b.update(duplicate_of=a["key"], duplicate_turns=k)
    # A byte-for-byte copy named the first file of its kind in this run before
    # the thumbnails found that file in an earlier dataset: point it past that
    # file too, adding the turns (rot90 by t1, then by t2, is rot90 by t1 + t2).
    by_key = {r["key"]: r for r in earlier + rows}
    for r in rows:
        for _ in range(len(by_key)):  # bounded, should a manifest hold a loop
            up = by_key.get(r["duplicate_of"])
            if up is None or not up["duplicate_of"]:
                break
            turns = int(r.get("duplicate_turns") or 0) + int(up.get("duplicate_turns") or 0)
            r.update(duplicate_of=up["duplicate_of"], duplicate_turns=turns % 4)


COLUMNS = [
    "key",
    "dataset",
    "id",
    "image",
    "mask",
    "mask_target",
    "tissue",
    "width",
    "height",
    "wound_fraction",
    "split",
    "patient",
    "duplicate_of",
    "duplicate_turns",
    "licence",
    "group",
    "note",
    "image_sha256",
    "wound_box_px",
    "marker_box_px",
]


USE = {
    "usable": "company use allowed, with credit",
    "confirm-first": "internal testing allowed, with credit; before any commercial use (the "
    "product, its training data or its marketing) get the authors' written confirmation of "
    "the licence - see each row's note",
    "noncommercial": "NON-COMMERCIAL: internal research only, after legal sign-off; never in the "
    "product, its training data or its marketing",
}


def write_licences(root: Path, names: list[str]) -> None:
    lines = [
        "# Licences and credit",
        "",
        "manifest.csv gives each photograph's dataset. Credit the dataset as below wherever "
        "its photographs or masks are shown or reported. A Creative Commons licence settles "
        "copyright, not patient consent: get legal and regulatory review before any of them "
        "appears in marketing, labelling or a submission.",
        "",
        "Changes made: masks/ holds each published wound mask redrawn as 0 (background) and 255 "
        "(wound), a pixel counting as wound where the published mask is at or over half its "
        "scale (or, in a palette image of coloured labels, has any index but 0), so grey edge "
        "pixels are rounded one way or the other. The published files are unchanged under "
        "raw/; photographs and tissue masks are copied byte for byte, each photograph named "
        "for the format it is in (.jpg for JPEG data, whatever the published suffix). Say so "
        "when you share the masks, as the licences require: for example, 'wound masks "
        "binarised from the published masks'.",
        "",
    ]
    for n in names:
        d = DATASETS[n]
        lines += [
            f"## {n}",
            "",
            f"- Licence: {d['licence']} ({d['licence_url']})",
            f"- Use: {USE[d['group']]}",
            f"- Source: {d['source']}",
            f"- Contents: {d['contents']}",
            f"- Credit: {d['attribution']}",
            "",
        ]
    (root / "LICENSES.md").write_text("\n".join(lines))


FOLDERS = ("raw", "images", "masks", "tissue")


def build(names: list[str], root: Path, earlier: list[Row]) -> list[Row]:
    # In DATASETS order whatever the command line said, so the copy of a
    # repeated photograph that is kept does not depend on how it was typed.
    names = [n for n in DATASETS if n in names]
    others = [
        n for n in DATASETS if n not in names and any((root / f / n).exists() for f in FOLDERS)
    ]
    if others:
        one = len(others) == 1
        sys.exit(
            f"{root} also holds {', '.join(others)}: name {'it' if one else 'them'} too, or "
            f"delete {'its' if one else 'their'} folders under {', '.join(FOLDERS)} first. "
            "manifest.csv and LICENSES.md are rewritten for the datasets named, and would "
            f"leave {'its' if one else 'their'} photographs unlisted."
        )
    for f in FOLDERS:  # a folder linked into a repository would take the files there
        for n in names:
            outside_git(root / f / n)
    rows: list[Row] = []
    for n in names:
        print(f"{n}:", flush=True)
        d = DATASETS[n]
        d["fetch"](root / "raw" / n)
        for r in d["layout"](root, root / "raw" / n):
            mask = np.asarray(Image.open(root / r["mask"])) > 0
            r.update(
                key=f"{n}/{r['id']}",
                dataset=n,
                mask_target=d.get("mask_target", "wound"),
                licence=d["licence"],
                group=d["group"],
                width=mask.shape[1],
                height=mask.shape[0],
                path=root / r["image"],
                wound_fraction=round(float(mask.mean()), 6),
                duplicate_of="",
                note="",
                image_sha256=hashlib.sha256((root / r["image"]).read_bytes()).hexdigest(),
            )
            rows.append(r)
        print(f"  {sum(r['dataset'] == n for r in rows)} photographs with masks", flush=True)
    mark_repeats(rows, earlier)
    fetched = set(names) | {r["dataset"] for r in earlier}
    for r in rows:
        if "note" in DATASETS[r["dataset"]]:
            r["note"] = DATASETS[r["dataset"]]["note"](r, fetched)
    with open(root / "manifest.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    write_licences(root, names)
    dup = sum(bool(r["duplicate_of"]) for r in rows)
    print(
        f"{root}: {len(rows)} photographs, {len(rows) - dup} distinct "
        f"({dup} repeat a photograph listed before them)"
    )
    return rows


def read_manifest(root: Path) -> list[Row]:
    """The rows of an earlier fetch, to check new photographs against."""
    if not (root / "manifest.csv").exists():
        return []
    with open(root / "manifest.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["path"] = root / r["image"]
    return rows


def main() -> int:
    default = [n for n, d in DATASETS.items() if d["group"] != "noncommercial"]
    gated = [n for n, d in DATASETS.items() if d["group"] == "noncommercial"]
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True, type=Path, help="folder outside any git work tree")
    ap.add_argument(
        "--datasets",
        nargs="*",
        default=default,
        choices=default,
        help="CC BY datasets (default: all of them); LICENSES.md says what each allows",
    )
    ap.add_argument(
        "--noncommercial",
        nargs="*",
        default=[],
        choices=gated,
        help="non-commercial datasets, after legal sign-off, into OUT/noncommercial/",
    )
    a = ap.parse_args()
    out = outside_git(a.out)
    rows = build(a.datasets, out, []) if a.datasets else read_manifest(out)
    if a.noncommercial:
        print(
            "NON-COMMERCIAL datasets: internal research only, after legal sign-off; never in "
            "the product, its training data or its marketing."
        )
        build(a.noncommercial, outside_git(out / "noncommercial"), rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
