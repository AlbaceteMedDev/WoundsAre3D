"""Assemble the reproduction kit for the lifelike phantoms W1-W8: one zip with
the specification, a data card per wound, every design input and the truth as
JSON, content hashes of the print files, the code with its exact font and
pinned requirements, pictures and the printing notes. With it the parts can be
rebuilt and checked on any computer, or studied in the sandbox of an AI
assistant that runs Python, such as ChatGPT, which can run preview_design.py
though not the full build.

    python make_repro_kit.py                # build/lifelike_wound_phantoms_kit.zip
    python make_repro_kit.py --out DIR

Run it in the environment that built lifelike/: it hashes those files, records
the library versions and draws the design previews, and stops if the previews
do not match the truth.
"""
import argparse
import hashlib
import io
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
import zipfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_lifelike as LL                  # noqa: E402
import make_phantoms_step as M              # noqa: E402
import check_reproduction as CR             # noqa: E402
import preview_design as PD                 # noqa: E402

KIT = "lifelike_wound_phantoms_kit"
CODE = ["make_lifelike.py", "make_phantoms_step.py", "verify_lifelike.py", "verify_labels.py",
        "render_lifelike.py", "render_parts.py", "preview_design.py", "check_reproduction.py"]
FACES = ["top", "front", "right", "back", "left", "bottom"]
PERI_NAMES = dict(ery="erythema", hae="haemosiderin", mac="maceration", cal="callus", pal="pale shiny skin")

# ------------------------------------------------------------------ colour ---
def hexof(c):
    return "#%06X" % LL.hexval(c)

def lab(h):
    """sRGB hex to CIELAB, D65, to 0.1."""
    c = np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)])/255.0
    c = np.where(c <= 0.04045, c/12.92, ((c + 0.055)/1.055)**2.4)
    xyz = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750],
                    [0.0193339, 0.1191920, 0.9503041]]) @ c/np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6/29)**3, np.cbrt(xyz), xyz/(3*(6/29)**2) + 4/29)
    return [round(float(v), 1) for v in (116*f[1] - 16, 500*(f[0] - f[1]), 200*(f[1] - f[2]))]

def colour(h):
    return dict(hex=h, lab=lab(h))

def layer_colours(w):
    """The colour each of a wound's periwound layers mixes towards."""
    d = LL.Design(w)
    x, y = np.array([LL.CENTRE[0]]), np.array([LL.PATCH[3] - 5.0])
    return {n: hexof(c) for n, _, c in d.periwound_layers(x, y, *d.frame(x, y))}

# -------------------------------------------------------------- parameters ---
def harmonics_calls():
    """Each wound's harmonics(...) call as written in make_lifelike.py."""
    src = open(os.path.join(HERE, "make_lifelike.py")).read()
    return dict(re.findall(r'id="(W\d+)".*?harm=(harmonics\([^)]*\))', src, re.S))

def parameters(truth):
    calls = harmonics_calls()
    wounds = []
    for w in LL.WOUNDS:
        e = {k: v for k, v in w.items() if k not in ("harm", "H")}
        e["block_height_mm"] = truth[w["id"]]["skin_plane_z_mm"]
        e["harmonics_call"] = calls[w["id"]]
        e["harmonics"] = [dict(m=m, A=A, phase_rad=ph) for m, A, ph in w["harm"]]
        e["periwound_layer_colours"] = {n: colour(h) for n, h in layer_colours(w).items()}
        wounds.append(e)
    return dict(
        about="Every design input of the lifelike phantoms W1-W8, read from make_lifelike.py and "
              "make_phantoms_step.py. SPEC.md explains each; the code is the reference.",
        units="millimetres; angles in degrees anticlockwise from 3 o'clock about the wound centre, "
              "+y towards 12 o'clock; colours sRGB with CIELAB (D65)",
        constants=dict(block_side_mm=LL.L, engraving_depth_mm=LL.ENG, patch_x0_x1_y0_y1_mm=list(LL.PATCH),
                       wound_centre_mm=list(LL.CENTRE), surface_mesh_half_width_mm=LL.FRAME,
                       max_triangle_area_mm2=dict(wound=LL.AREA_WOUND, periwound=LL.AREA_PERI,
                                                  beyond_patch=LL.AREA_FRAME),
                       max_triangles=LL.MAX_TRIANGLES, undermining_roof_mm=LL.ROOF,
                       tissue_priority=LL.ORDER),
        labels=dict(font="DejaVu Sans Mono Bold (code/fonts)", cap_height_min_mm=M.CAP_MIN,
                    cap_height_max_mm=M.CAP_MAX, cap_height_per_font_size=M.CAP_RATIO,
                    advance_per_font_size=M.ADV, line_pitch_per_cap=M.PITCH, extra_spacing_per_cap=M.TRACK,
                    min_land_mm=M.LAND_MIN, edge_clearance_mm=M.EDGE),
        top_marks=dict(key_line_length_mm=M.KEY_LEN, key_line_width_mm=M.KEY_W, key_line_y_mm=M.KEY_Y,
                       tick_width_mm=M.TICK_W, tick_height_mm=M.TICK_H, dot_radius_mm=M.DOT_R,
                       dot_centre_xy_mm=M.DOT_XY),
        colours=dict(
            skin={k: colour(hexof(v)) for k, v in LL.SKIN.items()},
            periwound={k: {PERI_NAMES[n]: colour(h) for n, h in v.items()} for k, v in LL.PERI_COL.items()},
            tissue={k: [colour(h) for h in v] for k, v in LL.TISSUE_REF.items()},
            body=colour(hexof(LL.BODY)), ink_dark=colour(hexof(LL.INK_DARK)),
            ink_light=colour(hexof(LL.INK_LIGHT))),
        wounds=wounds)

# -------------------------------------------------------------- data cards ---
def clock_of(deg):
    return LL.clock(math.radians(deg))

def pct_text(pc):
    return " · ".join(f"{n} {v}" for n, v in sorted(pc.items(), key=lambda i: -i[1]) if v > 0)

def peri_text(w):
    out = []
    for k, v in w["peri"].items():
        out.append({
            "erythema": lambda: f"erythema, width scale {v} mm",
            "haemosiderin": lambda: f"haemosiderin staining to about {v} mm out",
            "maceration": lambda: f"maceration {clock_of(v[1])} to {clock_of(v[0])} o'clock ({v[0]}°–{v[1]}°)",
            "maceration_ring": lambda: f"maceration ring, falling off over {v} mm",
            "callus": lambda: f"callus {v[0]} mm wide, {v[1]} mm high",
            "epibole": lambda: f"rolled edge {clock_of(v[1])} to {clock_of(v[0])} o'clock, {v[2]} mm high",
            "pallor": lambda: f"pale shiny skin, width scale {v} mm",
            "sutures": lambda: "incision line and suture marks every 7 mm",
        }[k]())
    return "; ".join(out) or "none: intact skin"

def features(w):
    out = []
    if w.get("islands"):
        out.append("islands of new epithelium (partial thickness)")
    if w.get("pale"):
        out.append("pale, poorly perfused granulation")
    if w.get("bone"):
        b = w["bone"]
        out.append(f"exposed bone: ellipse centred ({b['at'][0]:+.1f}, {b['at'][1]:+.1f}) mm from the wound "
                   f"centre, semi-axes {b['axes'][0]} × {b['axes'][1]} mm at {b['rot']}°; its share sets its size")
    if w.get("undermine"):
        u = w["undermine"]
        out.append(f"undermining {clock_of(u['end'])} to {clock_of(u['start'])} o'clock "
                   f"({u['start']}°–{u['end']}°), up to {u['extent']} mm, in a {u['height']} mm slot under a "
                   f"{LL.ROOF} mm roof")
    return out

def table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "---|"*len(head)]
    return out + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]

def summary_rows(truth):
    return [(t["id"], t["wound"], t["skin_type"],
             f"{t['length_mm']:.1f} × {t['width_mm']:.1f} × {t['max_depth_mm']:.2f}",
             f"{t['area_mm2']:.1f}", f"{t['volume_mm3']:.1f}", pct_text(t["tissue_pct"]), t["periwound"])
            for t in truth.values()]

SUMMARY_HEAD = ["Part", "Wound", "Skin", "L × W × D (mm)", "Area (mm²)", "Volume (mm³)",
                "Tissue % from above", "Periwound"]

def card(w, t, p):
    sk = hexof(LL.SKIN[w["skin"]])
    out = [f"## {w['id']} — {t['wound']}", "",
           f"![{w['id']}](pictures/renders/{w['id']}.png) "
           f"![{w['id']} from above](pictures/renders/{w['id']}_top.png)", "",
           f"Skin type {w['skin']} ({sk}) · periwound: {t['periwound'].lower()} · block "
           f"{t['block_mm'][0]:.0f} × {t['block_mm'][1]:.0f} × {t['block_mm'][2]:.0f} mm · "
           f"`{t['files'][0]}`, `{t['files'][1]}`", "",
           "**Design inputs** (`WOUNDS` in `code/make_lifelike.py`; all of them in `data/parameters.json`)", ""]
    rows = [("Semi-axes a (3–9 o'clock), b (12–6)", f"{w['a']} mm, {w['b']} mm"),
            ("Rotation", f"{w['rot']}°"),
            ("Outline irregularity", f"`{p['harmonics_call']}`: {len(w['harm'])} harmonics"),
            ("Depth D, wall shape k", f"{w['D']} mm, {w['k']}"),
            ("Target tissue shares", ", ".join(f"{n} {v:.2f}" for n, v in w["tissue"].items() if v > 0))]
    rows += [("Feature", f) for f in features(w)]
    rows += [("Periwound", peri_text(w)), ("Engraved periwound names", ", ".join(w["peri_names"])),
             ("Random seed", w["seed"])]
    out += table(["Input", "Value"], rows) + ["", "**Truth** (measured on the print mesh; "
                                              "`data/truth_lifelike.json`)", ""]
    u = t.get("undermining")
    vol = f"{t['volume_mm3']:.2f} mm³"
    if u:
        vol += f"; with the hidden {u['hidden_volume_mm3']:.2f} mm³ beyond the margin, {t['total_volume_mm3']:.2f} mm³"
    rows = [("Length (12–6) × width (3–9)", f"{t['length_mm']:.2f} × {t['width_mm']:.2f} mm"),
            ("Longest diameter", f"{t['longest_mm']:.2f} mm at {t['longest_angle_deg']:+.1f}° from 12–6; "
                                 f"width across it {t['width_across_longest_mm']:.2f} mm"),
            ("Area; perimeter", f"{t['area_mm2']:.2f} mm²; {t['perimeter_mm']:.2f} mm"),
            ("Maximum depth", f"{t['max_depth_mm']:.3f} mm below the skin plane, z = {t['skin_plane_z_mm']:.0f} mm"),
            ("Volume", vol),
            ("Tissue, % of the area from above", pct_text(t["tissue_pct"])),
            ("Tissue, % of the bed's surface", f"{pct_text(LL.pct(t['tissue_share_surface']))} "
                                               f"(of {t['bed_surface_area_mm2']:.1f} mm²)"),
            ("Mean printed tissue colour", ", ".join(f"{n} {h}" for n, h in t["tissue_colour"].items())),
            ("Part", f"{t['material_mm3']/1000:.1f} cm³ of material; {t['vertices']:,} vertices, "
                     f"{t['triangles']:,} triangles")]
    out += table(["Measure", "Value"], rows)
    if t["periwound_conditions"]:
        out += ["", "**Periwound** — where each change's weight is at least 0.3 (SPEC.md §8, §11)", ""]
        out += table(["Change", "Area (mm²)", "Clock hours", "Reaches (mm)", "Colour"],
                     [(c["name"], c["area_mm2"],
                       c["clock"] if isinstance(c["clock"], str) else ", ".join(map(str, c["clock"])),
                       c["reaches_mm"], p["periwound_layer_colours"][c["name"]]["hex"])
                      for c in t["periwound_conditions"]])
    if u:
        out += ["", f"**Undermining** — from the margin outward along a line from the wound centre; the "
                    f"pocket is {LL.ROOF} mm below the skin", ""]
        out += table(["Clock", "Extent (mm)", "Pocket height (mm)"],
                     [(h, u["extent_by_clock_mm"][h], u["pocket_height_by_clock_mm"].get(h, ""))
                      for h in map(str, [10, 11, 12, 1, 2])])
        out += ["", f"Maximum {u['max_extent_mm']:.1f} mm at {u['max_at_clock']} o'clock; undermined area "
                    f"{u['undermined_area_mm2']:.1f} mm²."]
    out += ["", "**Engraved labels**, 1.0 mm deep", ""]
    by = {f: [l for l in t["labels"] if l["face"] == f] for f in FACES}
    caps = lambda ls: sorted({l["cap_mm"] for l in ls}, reverse=True)
    out += table(["Face", "Cap height (mm)", "Lines"],
                 [(f, " / ".join(f"{c:.2f}" for c in caps(ls)),
                   " · ".join(f"`{l['text']}`" + (f" ({l['cap_mm']:.1f})" if len(caps(ls)) > 1 else "")
                              for l in ls))
                  for f, ls in by.items() if ls])
    return out + [""]

def data_cards(truth, params):
    out = ["# Lifelike wound phantoms W1–W8 — data cards", "",
           "One card per part, generated from `code/make_lifelike.py` and `data/truth_lifelike.json`. "
           "Millimetres; length runs from 12 to 6 o'clock (12 is the edge with the part number), width "
           "from 3 to 9, depth down from the skin plane. The design inputs make the part; the truth is "
           "measured on the mesh that is printed. SPEC.md defines every term.", ""]
    out += table(SUMMARY_HEAD, summary_rows(truth)) + [""]
    for w, p in zip(LL.WOUNDS, params["wounds"]):
        out += card(w, truth[w["id"]], p)
    return "\n".join(out)

# ------------------------------------------------------------- documents ---
def section(path, heading):
    """A '## ' section of a Markdown file, its heading included."""
    lines = open(path).read().split("\n")
    i = next(k for k, l in enumerate(lines) if l.startswith(heading))
    j = next((k for k in range(i + 1, len(lines)) if lines[k].startswith("## ")), len(lines))
    return "\n".join(lines[i:j]).rstrip() + "\n"

def extract(name, heading, pages):
    return (f"> From `docs/phantoms/{name}` in the repository, where paths are relative to "
            f"`docs/phantoms`. In this kit the code is in `code/`, the pictures in `pictures/`, and "
            f"`parts_sheet.pdf` pages {pages} are `pictures/parts_sheet_W1-W8.pdf`.\n\n"
            + section(os.path.join(HERE, name), heading))

def sheet_pages(src):
    """The parts sheet's pages for the W-series, as a PDF of their own."""
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(src)
    keep = [i for i in range(len(pdf))
            if pdf[i].get_textpage().get_text_range().lstrip().startswith("Lifelike colour wounds")]
    out, buf = pdfium.PdfDocument.new(), io.BytesIO()
    out.import_pages(pdf, keep)
    out.save(buf)
    return buf.getvalue(), f"{keep[0] + 1}–{keep[-1] + 1}"

def readme(truth, source):
    lines = [
        "# Lifelike wound phantoms W1–W8 — reproduction kit", "",
        "Everything needed to reproduce, check or change StrataMetric's eight full-colour 3D-printed wound "
        f"phantoms, W1–W8, or to study them with an AI assistant. Assembled {source}.", ""]
    lines += table(SUMMARY_HEAD, summary_rows(truth))
    lines += ["", """## What is here

| Path | What it is |
|---|---|
| `AI_ASSISTANT_START_HERE.md` | Using the kit with an AI assistant that runs Python, such as ChatGPT: what it can do, and prompts to paste |
| `SPEC.md` | The specification: coordinates, every formula, colours, labels, files, truth and verification |
| `DATA-CARDS.md` | A card per wound: design inputs, measured truth, periwound, colours and every engraved line |
| `data/parameters.json` | Every design input, machine-readable: constants, colours in hex and CIELAB, each wound with its outline harmonics |
| `data/truth_lifelike.json` | The ground truth of the printed parts, measured on the print meshes |
| `data/checksums.json` | Content hashes of each part's print files, and the versions and font that built them |
| `code/` | The generator and its checks, the exact font (`code/fonts/`), and pinned requirements |
| `pictures/renders/` | Each part drawn from its 3MF: at an angle, and the wound from above |
| `pictures/design/` | Each wound from above as designed — colour, tissue map, depth — by `preview_design.py` |
| `pictures/parts_sheet_W1-W8.pdf` | The printed parts sheet: each part's picture, sizes in mm and cm, tissue swatches |
| `docs/OVERVIEW.md`, `docs/ORDER-SHEET.md` | The set described and verified, and how to order the prints |
| `MANIFEST.sha256` | A SHA-256 for every file in the kit |

The print files themselves (a 3MF and a zipped VRML per part, about 70 MB) are not in the kit: they
are in the repository at `docs/phantoms/lifelike/`, and the build below writes them again.

## Reproducing

**1. The design — anywhere Python has numpy, scipy and matplotlib**, including an AI assistant's
sandbox. In `code/`:

    python preview_design.py

recomputes each wound's outline and sizes, tissue map, periwound and undermining with the same
functions the build uses, checks them against `data/truth_lifelike.json` and draws each wound into
`code/preview/`. It ends `ALL MATCH`, in about 30 seconds (`python preview_design.py W1 W2` does
just those).

**2. The print files — on a computer with Python 3.11** (Linux x86-64 for byte-identical files). In
`code/`:

    python3.11 -m venv .venv && . .venv/bin/activate      # Windows: .venv\\Scripts\\activate
    pip install -r requirements.txt
    python make_lifelike.py          # about 5 minutes for all eight; or name parts: W4 W6
    python check_reproduction.py     # IDENTICAL, or EQUIVALENT
    python verify_lifelike.py        # checks every file from the file alone: ALL OK

`make_lifelike.py` writes `code/lifelike/` and `code/truth_lifelike.json`. `check_reproduction.py`
compares them with `data/`: **IDENTICAL** — every file has the printed parts' content, byte for
byte; **EQUIVALENT** — other library versions or another platform triangulated differently, but
every number and label agrees, and `verify_lifelike.py` is then the check that counts.

**3. Pictures** (optional): `python render_lifelike.py` draws `code/renders/lifelike/` (headless
Linux needs `libosmesa6`).

## Changing a wound

Edit its entry in `WOUNDS` in `code/make_lifelike.py` (SPEC.md §17), look at it with
`python preview_design.py W3` — DIFF lines against the old truth are then expected — and build,
verify and render it. Every number engraved on a part follows from the geometry.

## Notes

- Millimetres throughout; 12 o'clock is the edge with the part number.
- No patient data or images are used. Colours come from published skin reflectance measurements,
  tissue-labelled ulcer photographs (LUTSeg, CC BY 4.0) and clinical descriptions; SPEC.md §12
  and §19 give the sources and limits.
- `code/fonts/DejaVuSansMono-Bold.ttf` is the file the labels were cut from (installed copies of
  DejaVu can differ), under its own licence, `code/fonts/LICENSE.txt`.
"""]
    return "\n".join(lines)

ASSISTANT = """# Using this kit with an AI assistant

The kit is made to be handed to an AI assistant that can run Python on uploaded files, such as
ChatGPT with its code tool. Upload the zip as it is.

## What the assistant can and cannot do

| Task | In the assistant's sandbox |
|---|---|
| Read and explain the specification, data cards and truth | Yes |
| Recompute each wound's sizes, tissue shares, periwound and undermining, and check them against the truth | Yes: `code/preview_design.py` needs only numpy, scipy and matplotlib |
| Draw each wound as designed — colour, tissue map, depth | Yes: `code/preview_design.py` |
| Change a wound's design and see what it does | Yes |
| Build the 3MF and VRML print files, verify and render them | Usually not: that needs cadquery, manifold3d and triangle, which a sandbox without internet cannot install. Do it on a computer (README.md, step 2) |

## First prompt

Attach the zip and paste:

> The attached zip is a reproduction kit for eight full-colour 3D-printed wound phantoms, W1–W8.
> 1. Unzip it. Read `README.md`, `SPEC.md` and `DATA-CARDS.md` in full.
> 2. In `lifelike_wound_phantoms_kit/code`, run `python preview_design.py W1 W2 W3 W4`, then
>    `python preview_design.py W5 W6 W7 W8`. Each run prints a block of checks per wound and ends
>    `ALL MATCH`. Show me the last lines of each run.
> 3. Show me the eight pictures it wrote to `code/preview/`.
> 4. Give me a table of the eight wounds — type, skin type, length × width × depth (mm), area (mm²),
>    volume (mm³), tissue percentages and periwound changes — from `data/truth_lifelike.json`.
>
> Treat the kit's files as the only source of truth: quote numbers from them and never estimate
> one. Say so if something cannot be done in your sandbox.

## Further prompts

- *How is W4's undermining modelled, and how far does a probe go in at each clock hour?*
- *Which numbers engraved on each part are measured on the mesh and which come from the design?
  Use SPEC.md §11.*
- *In `code/make_lifelike.py`, make W3 2 mm deeper (`D` from 7.0 to 9.0). Run
  `python preview_design.py W3` and tell me how the depth, volume and block height change.* (DIFF
  lines are expected: the truth file describes the printed part.)
- *Design a W9 following SPEC.md §17: a venous ulcer about 20 × 12 mm on skin type VI, 70 %
  granulation, 20 % slough, 10 % epithelium, with haemosiderin and erythema around it. Add it to
  `WOUNDS`, preview it, and show me its picture and numbers.*
- *Write a script that lists every engraved line on each face of each part, from
  `data/truth_lifelike.json`.*
- *From the CIELAB values in `data/parameters.json`, how far apart (ΔE) are granulation and the
  erythema of each skin type?*

## If something does not match

- `DIFF` lines with no file edited mean a file changed on the way: compare the files with
  `MANIFEST.sha256`. After editing a wound, DIFF lines for that wound are expected.
- `grid` rows are sampled on a 0.15 mm grid rather than measured on the print mesh, so they agree
  within tolerances (depth 0.05 mm, volume 2 %, colour 8 of 255), not exactly; `design` rows agree
  to rounding.
- A run that stops for time: run fewer wounds at once, e.g. `python preview_design.py W4`.
- A missing package: `preview_design.py` needs only numpy, scipy and matplotlib, never cadquery,
  manifold3d or triangle.
"""

PREVIEW_REQ = """# preview_design.py only: no meshing or CAD libraries. Tested with numpy 1.26
# and 2.4, scipy 1.11 and 1.17, matplotlib 3.8 and 3.11.
numpy
scipy
matplotlib
"""

# --------------------------------------------------------------------- main ---
def git(*args):
    return subprocess.run(["git", "-C", HERE, *args], capture_output=True, text=True).stdout.strip()

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=os.path.join(HERE, "build"))
    a = ap.parse_args()
    rows = json.load(open(os.path.join(HERE, "truth_lifelike.json")))
    truth = {r["id"]: r for r in rows}
    files = {}
    put = lambda name, data: files.__setitem__(name, data.encode() if isinstance(data, str) else data)

    # the design previews double as a check: the kit is not made if they disagree with the truth
    with tempfile.TemporaryDirectory() as tmp:
        bad = 0
        for w in LL.WOUNDS:
            _, _, r = PD.preview(w, truth[w["id"]], 0.15, tmp)
            bad += r.bad
            if r.bad:
                r.show()
            name = f"{w['id']}_{w['name']}_design.png"
            put(f"pictures/design/{name}", open(os.path.join(tmp, name), "rb").read())
        if bad:
            sys.exit(f"{bad} design values differ from truth_lifelike.json: rebuild before making the kit")
        CR.write(os.path.join(HERE, "lifelike"), os.path.join(HERE, "truth_lifelike.json"), tmp)
        put("data/checksums.json", open(os.path.join(tmp, "checksums.json"), "rb").read())

    sha, dirty = git("rev-parse", "--short", "HEAD"), git("status", "--porcelain", "--", ".")
    stamp = int(git("log", "-1", "--format=%ct") or time.time())
    source = (f"{time.strftime('%Y-%m-%d', time.gmtime(stamp))} from the WoundsAre3D repository, "
              f"`docs/phantoms` at commit {sha or 'unknown'}" + (" with uncommitted changes" if dirty else ""))
    params = parameters(truth)
    put("README.md", readme(truth, source))
    put("AI_ASSISTANT_START_HERE.md", ASSISTANT)
    put("SPEC.md", open(os.path.join(HERE, "LIFELIKE-SPEC.md")).read())
    put("DATA-CARDS.md", data_cards(truth, params))
    put("data/parameters.json", json.dumps(params, indent=1))
    put("data/truth_lifelike.json", open(os.path.join(HERE, "truth_lifelike.json"), "rb").read())
    for f in CODE:
        put(f"code/{f}", open(os.path.join(HERE, f), "rb").read())
    put("code/requirements.txt", open(os.path.join(HERE, "requirements-lifelike.txt"), "rb").read())
    put("code/requirements-preview.txt", PREVIEW_REQ)
    put("code/fonts/DejaVuSansMono-Bold.ttf", open(M.FONT_PATH, "rb").read())
    lic = [p for p in ("/usr/share/doc/fonts-dejavu-core/copyright",
                       os.path.join(os.path.dirname(M.FONT_PATH), "LICENSE_DEJAVU")) if os.path.exists(p)]
    if not lic:
        sys.exit("the DejaVu licence was not found: the font cannot go in the kit without it")
    put("code/fonts/LICENSE.txt", open(lic[0], "rb").read())
    for f in sorted(os.listdir(os.path.join(HERE, "renders", "lifelike"))):
        put(f"pictures/renders/{f}", open(os.path.join(HERE, "renders", "lifelike", f), "rb").read())
    pdf, pages = sheet_pages(os.path.join(HERE, "parts_sheet.pdf"))
    put("pictures/parts_sheet_W1-W8.pdf", pdf)
    put("docs/OVERVIEW.md", extract("INDEX.md", "## Lifelike colour set", pages))
    put("docs/ORDER-SHEET.md", extract("ORDER-SHEET.md", "## Lifelike colour set", pages))
    put("MANIFEST.sha256", "".join(f"{hashlib.sha256(files[n]).hexdigest()}  {n}\n" for n in sorted(files)))

    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, KIT + ".zip")
    when = time.gmtime(stamp)[:6]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for n in sorted(files):
            zi = zipfile.ZipInfo(f"{KIT}/{n}", date_time=when)
            zi.compress_type, zi.external_attr = zipfile.ZIP_DEFLATED, 0o644 << 16
            z.writestr(zi, files[n])
    print(f"{path}: {len(files)} files, {os.path.getsize(path)/1e6:.1f} MB")

if __name__ == "__main__":
    main()
