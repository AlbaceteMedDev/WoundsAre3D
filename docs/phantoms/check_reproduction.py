"""Check a rebuild of the lifelike phantoms W1-W8 against a reference: each
print file's content byte for byte, and the truth within tolerances. Python's
standard library only.

    python check_reproduction.py                   # lifelike/ and truth_lifelike.json beside this
                                                   # script, against ../data (the reproduction kit)
    python check_reproduction.py --reference DIR   # DIR holds checksums.json and truth_lifelike.json
    python check_reproduction.py --write DIR       # write DIR/checksums.json for the files here

IDENTICAL   every rebuilt file has the reference's content: expected with the
            versions in requirements.txt on Linux x86-64
EQUIVALENT  some content differs - other library versions or another platform
            can triangulate differently - but every truth value and label is
            within the tolerances below; verify_lifelike.py then checks the
            files themselves
DIFFERENT   a truth value or label is outside its tolerance
"""
import argparse
import hashlib
import json
import os
import platform
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SOFTWARE = ["numpy", "scipy", "triangle", "manifold3d", "cadquery", "cadquery-ocp", "matplotlib"]

# (absolute, relative) tolerance per truth field. The outline, tissue map,
# periwound and undermining extents are the same arithmetic on any platform;
# depth, volumes, surface areas and colours are measured on the mesh, which
# another triangulation changes slightly.
TOL = {
    "area_mm2": (0, 1e-6), "perimeter_mm": (0, 1e-6), "length_mm": (0, 1e-6), "width_mm": (0, 1e-6),
    "longest_mm": (0, 1e-6), "longest_angle_deg": (1e-3, 0), "width_across_longest_mm": (0, 1e-6),
    "tissue_share": (1e-4, 0), "tissue_pct": (0, 0), "periwound_conditions": (0.15, 0),
    "skin_plane_z_mm": (0, 0), "block_mm": (0, 0),
    "max_depth_mm": (0.005, 0), "volume_mm3": (0.05, 1e-3), "total_volume_mm3": (0.05, 2e-3),
    "undermining": (1e-3, 2e-3), "tissue_share_surface": (5e-3, 0), "bed_surface_area_mm2": (0.5, 5e-3),
    "tissue_colour": (2, 0), "material_mm3": (0.5, 1e-3),
}

def agree(a, b, ab=0.0, rel=1e-6):
    """Equal, or numbers within tolerance, through lists and dicts."""
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(agree(a[k], b[k], ab, rel) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(agree(p, q, ab, rel) for p, q in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= max(ab, rel*max(abs(a), abs(b)))
    return a == b

def rgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]

def contents(folder, row):
    """sha256 of the model inside a part's 3MF and of the VRML inside its zip:
    the zip containers carry timestamps; their contents do not."""
    f3, fw = (os.path.join(folder, f) for f in row["files"])
    with zipfile.ZipFile(f3) as z:
        model = hashlib.sha256(z.read("3D/3dmodel.model")).hexdigest()
    with zipfile.ZipFile(fw) as z:
        wrl = hashlib.sha256(z.read(z.namelist()[0])).hexdigest()
    return {"3mf_model_sha256": model, "wrl_sha256": wrl}

def software():
    from importlib.metadata import version, PackageNotFoundError
    out = {"python": platform.python_version(), "platform": f"{platform.system()} {platform.machine()}"}
    for name in SOFTWARE:
        try:
            out[name] = version(name)
        except PackageNotFoundError:
            out[name] = None
    try:                                            # the face the labels are cut from
        sys.path.insert(0, HERE)
        import make_phantoms_step as M
        out["font_sha256"] = hashlib.sha256(open(M.FONT_PATH, "rb").read()).hexdigest()
    except ImportError:
        out["font_sha256"] = None
    return out

def write(folder, truth_path, out_dir):
    rows = json.load(open(truth_path))
    sums = dict(about="Content hashes of each part's print files: the model inside the 3MF and the "
                      "text inside the VRML zip. check_reproduction.py compares a rebuild with them.",
                software=software(),
                parts={r["id"]: dict(files=r["files"], vertices=r["vertices"], triangles=r["triangles"],
                                     **contents(folder, r)) for r in rows})
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "checksums.json"), "w") as f:
        json.dump(sums, f, indent=1)
    return sums

def compare_truth(new, ref):
    """The fields outside tolerance, and labels that differ."""
    bad = []
    for k, (ab, rel) in TOL.items():
        x, y = new.get(k), ref.get(k)
        if k == "tissue_colour" and x and y:
            x, y = ({n: rgb(c) for n, c in v.items()} for v in (x, y))
        if not agree(x, y, ab, rel):
            bad.append(k)
    lines = lambda r: [(l["face"], l["text"]) for l in r["labels"]]
    place = lambda r: [l["at"] + [l["cap_mm"]] for l in r["labels"]]
    if lines(new) != lines(ref):
        bad.append("labels (text)")
    elif not agree(place(new), place(ref), 0.01, 0):
        bad.append("labels (position)")
    return bad

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--build", default=os.path.join(HERE, "lifelike"), help="folder of rebuilt print files")
    ap.add_argument("--truth", default=os.path.join(HERE, "truth_lifelike.json"), help="rebuilt truth")
    ap.add_argument("--reference", default=os.path.join(HERE, os.pardir, "data"))
    ap.add_argument("--write", metavar="DIR", help="write DIR/checksums.json for --build and --truth")
    a = ap.parse_args()
    if a.write:
        sums = write(a.build, a.truth, a.write)
        print(f"wrote checksums for {', '.join(sums['parts'])} to {a.write}")
        return 0
    if not os.path.exists(a.truth):
        sys.exit(f"no rebuilt truth at {a.truth}: run make_lifelike.py first")
    ref_sums = json.load(open(os.path.join(a.reference, "checksums.json")))
    ref_truth = {r["id"]: r for r in json.load(open(os.path.join(a.reference, "truth_lifelike.json")))}
    new_truth = {r["id"]: r for r in json.load(open(a.truth))}
    same_all, bad_all = True, 0
    for pid in sorted(new_truth, key=lambda s: int(s[1:])):
        row = new_truth[pid]
        if not all(os.path.exists(os.path.join(a.build, f)) for f in row["files"]):
            print(f"{pid}: files not found in {a.build}; skipped")
            continue
        same = contents(a.build, row) == {k: ref_sums["parts"][pid][k] for k in ("3mf_model_sha256", "wrl_sha256")}
        bad = compare_truth(row, ref_truth[pid])
        same_all &= same
        bad_all += len(bad)
        state = "identical files" if same else "files differ"
        print(f"{pid}: {state}; truth {'agrees' if not bad else 'differs in ' + ', '.join(bad)}")
    print("built with:", json.dumps(software()))
    print("reference: ", json.dumps(ref_sums["software"]))
    verdict = "IDENTICAL" if same_all and not bad_all else "EQUIVALENT" if not bad_all else "DIFFERENT"
    print(verdict + ("" if verdict == "IDENTICAL" else
                     " - now run verify_lifelike.py" if verdict == "EQUIVALENT" else ""))
    return 0 if verdict != "DIFFERENT" else 1

if __name__ == "__main__":
    sys.exit(main())
