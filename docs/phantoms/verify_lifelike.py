"""Checks every lifelike phantom from its 3MF file - the file that is printed -
rather than from the generator's in-memory geometry.

For each part:
  - the mesh is one valid closed solid, under the triangle limit, in colour;
  - every engraved line, sliced 0.5 mm into its face, opens exactly as many
    glyphs as its text has (counted from the font, not from the generator), with
    at least 0.55 mm of material between neighbouring glyphs;
  - the numbers engraved are the numbers in truth_lifelike.json;
  - the truth itself, re-measured on the loaded mesh: the opening sliced just
    below the skin plane (area, perimeter, length, width), the volume under the
    skin plane inside the margin, the maximum depth, and on W4 the hidden
    undermining volume;
  - the printed colours: the wound bed's triangles, classed by nearest tissue
    colour, give tissue shares close to the labelled percentages.

    python verify_lifelike.py          # all parts
    python verify_lifelike.py W4       # just these
"""
import json
import math
import os
import re
import sys
import numpy as np
from scipy.spatial import cKDTree
from manifold3d import Manifold, Mesh, CrossSection
import make_lifelike as LL
import make_phantoms_step as M
from render_lifelike import read_3mf
from verify_labels import pieces

HERE = os.path.dirname(os.path.abspath(__file__))
SLICE = 0.5             # mm into each labelled face
LAND = 0.55             # mm of material between glyph openings
TOL_AREA = 0.01         # opening re-measured from a slice: within 1 %
TOL_VOL = 1e-4          # volume re-measured on the loaded mesh: within 0.01 %
TOL_TISSUE = 0.08       # colour-classed tissue shares: within 8 points

def load(path):
    v, t, rgb = read_3mf(path)
    m = Mesh(vert_properties=np.ascontiguousarray(v, np.float32),
             tri_verts=np.ascontiguousarray(t, np.uint32))
    m.merge()
    return Manifold(m), v, t, rgb

def polys(cs):
    out = []
    for p in cs.to_polygons():
        p = np.asarray(p)
        a = 0.5*np.sum(p[:, 0]*np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1)*p[:, 1])
        out.append((p, a))
    return out

def face_frame(xdir, normal):
    n = np.asarray(normal, float); u = np.asarray(xdir, float)
    v = np.cross(n, u)
    return np.vstack([u, v, n])

def check_label(part, row):
    R = face_frame(row["xdir"], row["normal"])
    at = np.asarray(row["at"], float)
    m = part.transform(np.c_[R, np.zeros(3)])
    z_face = float(at @ R[2])
    ps = polys(m.slice(z_face - SLICE))
    cu, cv = float(at @ R[0]), float(at @ R[1])
    hl = M.text_len(row["text"], row["cap_mm"])/2 + 0.6
    hh = row["cap_mm"]/2 + 0.6
    hs = []
    for p, a in ps:
        if a >= 0:
            continue
        c = p.mean(axis=0)
        if abs(c[0] - cu) <= hl and abs(c[1] - cv) <= hh:
            hs.append(p)
    want = pieces(row["text"])
    land = math.inf
    for i in range(len(hs)):
        others = [hs[j] for j in range(len(hs)) if j != i]
        if not others:
            continue
        tree = cKDTree(np.vstack(others))
        d, _ = tree.query(hs[i])
        land = min(land, float(d.min()))
    return len(hs), want, land

def numbers(text):
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)]

def check_text(row, t, w):
    """Each engraved figure must be the truth rounded as engraved."""
    s = row["text"]
    exp = {
        "AREA": f"{t['area_mm2']:.1f}", "VOL": f"{t['volume_mm3']:.1f}",
        "PERIM": f"{t['perimeter_mm']:.1f}",
    }
    for k, val in exp.items():
        if s.startswith(k + " ") and val not in s:
            return f"{s!r} should carry {val}"
    if s.startswith("L") and " W" in s and " D" in s:
        want = f"L{t['length_mm']:.1f} W{t['width_mm']:.1f} D{t['max_depth_mm']:.2f}"
        if s != want:
            return f"{s!r} should be {want!r}"
    if s.startswith("PCT") or any(s.startswith(LL.SHORT[n]) for n in LL.ORDER):
        for name, short in LL.SHORT.items():
            mm = re.search(rf"\b{short} (\d+)\b", s)
            if mm and int(mm.group(1)) != t["tissue_pct"][name]:
                return f"{s!r}: {short} should be {t['tissue_pct'][name]}"
    if "undermining" in t:
        u = t["undermining"]
        if s.startswith("HIDDEN") and f"{u['hidden_volume_mm3']:.1f}" not in s:
            return f"{s!r} should carry {u['hidden_volume_mm3']:.1f}"
        if s.startswith("MAX") and f"{u['max_extent_mm']:.1f}" not in s:
            return f"{s!r} should carry {u['max_extent_mm']:.1f}"
    return None

def tissue_from_colour(v, t, rgb, w, H):
    """Area shares of each tissue in the wound bed, classing each upward-facing
    triangle inside the margin by the nearest tissue colour range."""
    p = v[t]
    cen = p.mean(axis=1)
    r, th = LL.polar(cen[:, 0], cen[:, 1])
    inside = r < LL.r_of(w, th) - 0.3
    nrm = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    up = nrm[:, 2] > 0
    sel = inside & up & (cen[:, 2] < H - 0.02)
    area = 0.5*nrm[sel, 2]
    col = rgb[sel].mean(axis=1)/255.0
    use = {"granulation": "granulation_pale" if w.get("pale") else "granulation",
           "slough": "slough", "necrotic": "necrotic",
           "epithelial": "epithelial_dark" if LL.luminance(LL.SKIN[w["skin"]]) < 0.47 else "epithelial"}
    # only the tissues this part has: on dark skin, new epithelium and the pale
    # granulation of an arterial ulcer are close in colour, as they are in life
    use = {n: k for n, k in use.items() if w["tissue"].get(n, 0) > 0}
    refs, names = [], []
    for name, key in use.items():
        hexes = LL.TISSUE_REF[key]
        for a, b in zip(hexes[:-1], hexes[1:]):                 # along each tissue's range
            for k in np.linspace(0, 1, 4):
                refs.append(LL.rgb(a)*(1 - k) + LL.rgb(b)*k); names.append(name)
    refs = np.array(refs)
    idx = np.argmin(((col[:, None, :] - refs[None])**2).sum(-1), axis=1)
    out = {n: 0.0 for n in LL.ORDER}
    for i, a in zip(idx, area):
        out[names[i]] += a
    tot = sum(out.values())
    return {n: out[n]/tot for n in out}

def check(w, row):
    errs = []
    path = os.path.join(LL.OUT, row["files"][0])
    part, v, t, rgb = load(path)
    H = row["skin_plane_z_mm"]
    if part.status().name != "NoError" or len(part.decompose()) != 1 or part.volume() <= 0:
        errs.append("not one valid solid")
    if len(t) > LL.MAX_TRIANGLES:
        errs.append(f"{len(t):,} triangles")
    ncol = len(np.unique(rgb.reshape(-1, 3), axis=0))
    # labels
    worst_land, bad = math.inf, []
    for lab in row["labels"]:
        got, want, land = check_label(part, lab)
        if got != want:
            bad.append(f"{lab['face']} {lab['text']!r}: {got} openings, expected {want}")
        if got > 1:
            worst_land = min(worst_land, land)
        e = check_text(lab, row, w)
        if e:
            errs.append(e)
    errs += bad
    if worst_land < LAND:
        errs.append(f"glyphs only {worst_land:.3f} mm apart")
    # truth, re-measured on the file
    ps = polys(part.slice(H - 0.003))
    holes = [(p, -a) for p, a in ps if a < 0]
    p, area = max(holes, key=lambda h: h[1] if np.hypot(*(h[0].mean(axis=0) - np.array(LL.CENTRE))) < 10 else 0)
    per = float(np.sum(np.hypot(*np.diff(np.vstack([p, p[:1]]), axis=0).T)))
    meas = dict(area=area, perimeter=per, length=float(np.ptp(p[:, 1])), width=float(np.ptp(p[:, 0])))
    for k, key in (("area", "area_mm2"), ("perimeter", "perimeter_mm"), ("length", "length_mm"), ("width", "width_mm")):
        if abs(meas[k] - row[key]) > TOL_AREA*row[key] + (0.1 if k in ("length", "width") else 0):
            errs.append(f"{k}: slice {meas[k]:.2f} vs truth {row[key]:.2f}")
    o, _ = LL.outline(w)
    z0 = M.ENG + 1.0                         # clear of the engraved underside
    prism = Manifold.extrude(CrossSection([o.tolist()]), H - z0).translate((0, 0, z0))
    vol = (prism - part).volume()
    if abs(vol - row["volume_mm3"]) > TOL_VOL*row["volume_mm3"] + 0.05:
        errs.append(f"volume: file {vol:.2f} vs truth {row['volume_mm3']:.2f}")
    r, th = LL.polar(v[:, 0], v[:, 1])
    ins = (r < LL.r_of(w, th) - 1e-6) & (v[:, 2] > z0)
    dep = H - v[ins, 2].min()
    if abs(dep - row["max_depth_mm"]) > 1e-3:
        errs.append(f"depth: file {dep:.4f} vs truth {row['max_depth_mm']:.4f}")
    hidden = None
    if "undermining" in row:
        thf = np.linspace(0, 2*math.pi, 20000, endpoint=False)
        rf = LL.r_of(w, thf) + LL.undermine_extent(w, thf)
        big = np.c_[LL.CENTRE[0] + rf*np.cos(thf), LL.CENTRE[1] + rf*np.sin(thf)]
        ring = Manifold.extrude(CrossSection([big.tolist()]), H - z0).translate((0, 0, z0)) - prism
        hidden = (ring - part).volume()
        u = row["undermining"]
        if abs(hidden - u["hidden_volume_mm3"]) > TOL_VOL*u["hidden_volume_mm3"] + 0.05:
            errs.append(f"hidden volume: file {hidden:.2f} vs truth {u['hidden_volume_mm3']:.2f}")
    # colour
    sh = tissue_from_colour(v, t, rgb, w, H)
    for n in LL.ORDER:
        if abs(sh[n] - row["tissue_share"][n]) > TOL_TISSUE:
            errs.append(f"{n}: colour share {sh[n]:.2f} vs labelled {row['tissue_share'][n]:.2f}")
    return errs, dict(triangles=len(t), colours=ncol, area=meas["area"], perimeter=per,
                      volume=vol, depth=dep, hidden=hidden, land=worst_land, colour_share=sh,
                      labels=len(row["labels"]))

def main(ids):
    rows = {r["id"]: r for r in json.load(open(os.path.join(HERE, "truth_lifelike.json")))}
    ok = True
    print(f"{'part':4} {'tris':>9} {'cols':>6} {'labels':>6} {'land':>6} {'area':>9} {'vol':>9} "
          f"{'depth':>6}  colour shares (gran/slough/nec/epi)  result")
    for w in LL.WOUNDS:
        if ids and w["id"] not in ids:
            continue
        errs, m = check(w, rows[w["id"]])
        sh = m["colour_share"]
        print(f"{w['id']:4} {m['triangles']:>9,} {m['colours']:>6} {m['labels']:>6} {m['land']:>6.3f} "
              f"{m['area']:>9.2f} {m['volume']:>9.2f} {m['depth']:>6.2f}  "
              f"{sh['granulation']:.2f}/{sh['slough']:.2f}/{sh['necrotic']:.2f}/{sh['epithelial']:.2f}"
              f"  {'OK' if not errs else 'FAIL'}")
        for e in errs:
            print("     ", e)
        ok &= not errs
    print("ALL OK" if ok else "FAILURES")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main(set(sys.argv[1:]))
