"""Check every engraving glyph by glyph on the delivered STEP files, and render
each labelled face the way it will read.

Each face is sliced parallel to itself at three depths. At 0.1 mm and at
ENG - 0.1 mm every glyph of every label must show up as its own opening, so the
whole label is there at full depth; at ENG + 0.2 mm no label opening may remain.
Every other opening in a slice has to be a feature the part is meant to have
(cavity, fiducials, key line, vents) - anything else, such as a vent breaking out
through a face, fails the part. Revision B would have failed here twice over: its
labels engraved one glyph per line, and P9's vents cut open slots in its top.

    python verify_labels.py            # check every part, write labels_preview/*.png
    python verify_labels.py P9 L2      # just these
"""
import json, math, os, sys
import numpy as np
import cadquery as cq
from OCP.STEPControl import STEPControl_Reader
import make_phantoms_step as M

HERE = os.path.dirname(os.path.abspath(__file__))
PREVIEW = os.path.join(HERE, "labels_preview")
DEPTHS = (0.1, M.ENG - 0.1, M.ENG + 0.2)

def load(fn):
    r = STEPControl_Reader(); r.ReadFile(os.path.join(M.OUT, fn)); r.TransferRoots()
    return cq.Shape.cast(r.OneShape())

def V(t): return cq.Vector(*t)

def frame(normal, xdir, origin):
    n, x = V(normal).normalized(), V(xdir).normalized()
    return V(origin), x, n.cross(x), n            # origin, u, v (text up), outward normal

def slice_plane(shape, origin, n, d, size=300.0):
    """The part's cross-section on the plane `d` inside a planar face."""
    pl = cq.Face.makePlane(size, size, (V(origin) - n*d), n)
    return shape.intersect(pl)

def slice_cyl(shape, p, d):
    """Cross-section `d` beneath the curved-limb phantom's cylindrical top."""
    Rc, H = p["cyl"], p["height"]
    cyl = cq.Solid.makeCylinder(Rc - d, M.L + 20, cq.Vector(0, -(M.L/2 + 10), H - Rc),
                                cq.Vector(0, 1, 0))
    face = [f for f in cyl.Faces() if f.geomType() == "CYLINDER"][0]
    # turn the cylinder's seam to the underside, or the slice is split along the
    # top and openings that straddle it stop being inner wires
    face = face.rotate(cq.Vector(0, 0, H - Rc), cq.Vector(0, 1, H - Rc), 180)
    return shape.intersect(face)

def holes(sec):
    """Every opening in a slice: an inner wire of one of its faces."""
    out = []
    for f in sec.Faces():
        for w in f.innerWires():
            out.append(w.BoundingBox())
    return out

def uv(pt, fr):
    o, u, v, _ = fr
    q = V(pt) - o
    return q.dot(u), q.dot(v)

def centre(bb):
    return ((bb.xmin + bb.xmax)/2, (bb.ymin + bb.ymax)/2, (bb.zmin + bb.zmax)/2)

_PIECES = {}

def pieces(txt):
    """How many separate openings a line should cut: each character rendered on
    its own from the font file, with the zero as a plain ring. Counted without
    the generator's spacing code, so a glyph that code lost would show here."""
    n = 0
    for ch in txt:
        if ch == " ":
            continue
        if ch not in _PIECES:
            t = (cq.Workplane("XY").text(ch, 10.0, 1.0, combine=False, font=M.FONT,
                                         fontPath=M.FONT_PATH, kind=M.KIND).val())
            _PIECES[ch] = 1 if ch == "0" else (len(t.Solids()) or 1)
        n += _PIECES[ch]
    return n

LAND_CHECK = 0.55       # material between neighbouring glyphs' grooves, mm

def min_land(sec, fr, inside):
    """Narrowest strip of material between two separate openings whose centres
    pass `inside(u, v)`, measured on the slice: the ridge a print has to hold up
    between two letters."""
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    ws = []
    for f in sec.Faces():
        for w in f.innerWires():
            if inside(*uv(centre(w.BoundingBox()), fr)):
                ws.append((w, w.BoundingBox()))
    best, at = math.inf, None
    for i in range(len(ws)):
        wi, bi = ws[i]
        for wj, bj in ws[i + 1:]:
            if (bi.xmin - bj.xmax > 2 or bj.xmin - bi.xmax > 2 or bi.ymin - bj.ymax > 2 or
                    bj.ymin - bi.ymax > 2 or bi.zmin - bj.zmax > 2 or bj.zmin - bi.zmax > 2):
                continue
            d = BRepExtrema_DistShapeShape(wi.wrapped, wj.wrapped); d.Perform()
            if d.Value() < best:
                p = d.PointOnShape1(1)
                best, at = d.Value(), uv((p.X(), p.Y(), p.Z()), fr)
    return best, at

# ------------------------------------------------------------ expectations ---
def face_labels(row, face):
    return [l for l in row.get("labels", []) if l["face"] == face]

def top_features(p):
    """Openings a block's top must show above ENG: cavity, dots, key, and the two
    top-face texts (as glyph counts)."""
    feats = []
    if p["kind"] != "flat":
        feats.append(("cavity", (0.0, 0.0), 1))
    for sx in (-1, 1):
        for sy in (-1, 1):
            feats.append(("dot", (sx*M.DOT_XY, sy*M.DOT_XY), 1))
    if p.get("key_axis") == "y":
        feats.append(("key", (M.KEY_Y, 0.0), 1))
    else:
        feats.append(("key", (0.0, M.KEY_Y), 1))
    if p["kind"] == "cylwell":
        feats.append(("index", (p["pocket_r"] + M.INDEX_GAP + M.INDEX_LEN/2, 0.0), 1))
    return feats

def top_texts(p):
    key, k = f"{M.KEY_LEN:.3f}", M.key_label(p)
    turned = abs(k["angle"]) == 90.0
    kl = M.text_len(key, M.CAP_MIN)/2 + 0.6
    return [("id", (0.0, 33.0), pieces(p["id"]),
             (M.text_len(p["id"], 6.0)/2 + 0.6, 0.75*6.0)),
            ("key label", (k["x"], k["y"]),
             pieces(key),
             (0.75*M.CAP_MIN, kl) if turned else (kl, 0.75*M.CAP_MIN))]

def classify(hs, fr, rects, feats, tol=3.0):
    """Assign each opening to a label rectangle or a known feature; the rest are
    unexpected."""
    per_rect = [0]*len(rects)
    per_feat = [0]*len(feats)
    stray = []
    for bb in hs:
        cu, cv = uv(centre(bb), fr)
        hit = False
        for i, (u0, v0, hw, hh) in enumerate(rects):
            if abs(cu - u0) <= hw and abs(cv - v0) <= hh:
                per_rect[i] += 1; hit = True; break
        if hit:
            continue
        for i, (_, (fu, fv), _) in enumerate(feats):
            if abs(cu - fu) <= tol and abs(cv - fv) <= tol:
                per_feat[i] += 1; hit = True; break
            if feats[i][0] == "cavity" and math.hypot(cu - fu, cv - fv) < 30:
                per_feat[i] += 1; hit = True; break
            if feats[i][0] == "key" and abs(cu - fu) <= 30 and abs(cv - fv) <= 4:
                per_feat[i] += 1; hit = True; break
        if not hit:
            stray.append((round(cu, 1), round(cv, 1)))
    return per_rect, per_feat, stray

# ----------------------------------------------------------------- render ---
def draw(ax, sec, fr, title, extent):
    from matplotlib.collections import PolyCollection
    polys = []
    for f in sec.Faces():
        vs, tris = f.tessellate(0.02, 0.2)
        pts = [uv(v.toTuple(), fr) for v in vs]
        polys += [[pts[a], pts[b], pts[c]] for a, b, c in tris]
    ax.add_collection(PolyCollection(polys, facecolors="#5b6470", edgecolors="none"))
    ax.set_xlim(extent[0], extent[1]); ax.set_ylim(extent[2], extent[3])
    ax.set_aspect("equal"); ax.set_title(title, fontsize=9); ax.set_xticks([]); ax.set_yticks([])

# ------------------------------------------------------------------- check ---
def in_rects(rects):
    return lambda u, v: any(abs(u - u0) <= hw and abs(v - v0) <= hh for (u0, v0, hw, hh) in rects)

def check_block(row, p, shape, panels):
    ok, notes, land = True, [], (math.inf, None)
    H = p["height"]
    for name, normal, xdir in M.SIDES + [("bottom", (0, 0, -1), (1, 0, 0))]:
        if name == "bottom":
            fr = frame(normal, xdir, (0, 0, 0))
        else:
            fr = frame(normal, xdir, (normal[0]*M.L/2, normal[1]*M.L/2, 0))
        labs = face_labels(row, name)
        rects, want = [], []
        for l in labs:
            u0, v0 = uv(l["at"], fr)
            rects.append((u0, v0, M.text_len(l["text"], l["cap_mm"])/2 + 0.6, 0.75*l["cap_mm"]))
            want.append(pieces(l["text"]))
        vent = row.get("vents") or {}
        n_vent = vent["count"] if name == "bottom" and vent else 0
        for d in DEPTHS:
            hs = holes(slice_plane(shape, fr[0], fr[3], d))
            # a vent is a round opening of the vent's size where a vent should be
            def is_vent(bb):
                if not n_vent:
                    return False
                cu, cv = uv(centre(bb), fr)
                size = sorted([bb.xlen, bb.ylen, bb.zlen])[1:]
                round_ = all(abs(s - vent["dia"]) < 0.3 for s in size)
                return round_ and any(abs(cu - x) < 0.5 and abs(cv + y) < 0.5
                                      for (x, y) in M.BOTTOM_VENTS)
            vh = [bb for bb in hs if is_vent(bb)]
            rest = [bb for bb in hs if not is_vent(bb)]
            if len(vh) != n_vent:
                ok = False; notes.append(f"{name}: {len(vh)} vents at {d} mm, expected {n_vent}")
            per_rect, _, stray = classify(rest, fr, rects, [])
            for l, w, got in zip(labs, want, per_rect):
                exp = w if d < M.ENG else 0
                if got != exp:
                    ok = False
                    notes.append(f"{name} '{l['text']}': {got} openings at {d} mm, expected {exp}")
            if stray:
                ok = False; notes.append(f"{name}: unexpected openings at {d} mm at {stray[:6]}")
        if labs:
            mid = slice_plane(shape, fr[0], fr[3], M.ENG/2)
            ld, at = min_land(mid, fr, in_rects(rects))
            if ld < LAND_CHECK:
                ok = False; notes.append(f"{name}: {ld:.3f} mm between grooves at {at}")
            land = min(land, (ld, f"{name} {tuple(round(a, 1) for a in at)}"), key=lambda t: t[0])
            if panels is not None:
                panels.append((name, mid, fr))
    # top
    fr = frame((0, 0, 1), (1, 0, 0), (0, 0, H))
    texts = top_texts(p)
    rects = [(c[0], c[1], hw, hh) for _, c, _, (hw, hh) in texts]
    feats = top_features(p)
    for d in DEPTHS:
        sec = slice_cyl(shape, p, d) if p.get("cyl") else slice_plane(shape, fr[0], fr[3], d)
        per_rect, per_feat, stray = classify(holes(sec), fr, rects, feats)
        for (nm, _, w, _), got in zip(texts, per_rect):
            exp = w if d < M.ENG else 0
            if got != exp:
                ok = False; notes.append(f"top {nm}: {got} openings at {d} mm, expected {exp}")
        for (nm, _, k), got in zip(feats, per_feat):
            exp = k if (d < M.ENG or nm == "cavity") else 0
            if got != exp:
                ok = False; notes.append(f"top {nm}: {got} at {d} mm, expected {exp}")
        if stray:
            ok = False; notes.append(f"top: unexpected openings at {d} mm at {stray[:6]}")
    sec = slice_cyl(shape, p, M.ENG/2) if p.get("cyl") else slice_plane(shape, fr[0], fr[3], M.ENG/2)
    ld, at = min_land(sec, fr, in_rects(rects))
    if ld < LAND_CHECK:
        ok = False; notes.append(f"top: {ld:.3f} mm between grooves at {at}")
    land = min(land, (ld, f"top {tuple(round(a, 1) for a in at)}"), key=lambda t: t[0])
    if panels is not None:
        panels.append(("top" + (" (curved; plan view)" if p.get("cyl") else ""), sec, fr))
    return ok, notes, land

def check_lid(row, l, shape, panels):
    ok, notes, land = True, [], (math.inf, None)
    fr = frame((0, 0, -1), (1, 0, 0), (0, 0, 0))
    want = sum(pieces(t) for t in M.lid_lines(l))
    for d in DEPTHS:
        hs = holes(slice_plane(shape, fr[0], fr[3], d))
        ring = [bb for bb in hs if M.LID_RC - 4 < math.hypot(*centre(bb)[:2]) < M.LID_RC + 4]
        other = [bb for bb in hs if bb not in ring]
        exp = want if d < M.ENG else 0
        if len(ring) != exp:
            ok = False; notes.append(f"underside: {len(ring)} glyph openings at {d} mm, expected {exp}")
        if len(other) != 1:                       # the wound hole itself
            ok = False; notes.append(f"underside: {len(other)} other openings at {d} mm, expected 1")
    top = holes(slice_plane(shape, (0, 0, l["thick"]), cq.Vector(0, 0, 1), 0.1))
    if len(top) != 1:
        ok = False; notes.append(f"top face: {len(top)} openings, expected only the hole")
    # the rim notch: open at +x, and only there
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.TopAbs import TopAbs_OUT
    from OCP.gp import gp_Pnt
    def out(x, y):
        c = BRepClass3d_SolidClassifier(shape.wrapped, gp_Pnt(x, y, l["thick"]/2), 1e-6)
        return c.State() == TopAbs_OUT
    r = l["R_out"] - M.NOTCH_D/2
    if not out(r, 0.0) or out(0.0, r) or out(-r, 0.0) or out(0.0, -r):
        ok = False; notes.append("rim notch missing, or not only at +x")
    mid = slice_plane(shape, fr[0], fr[3], M.ENG/2)
    ld, at = min_land(mid, fr, lambda u, v: M.LID_RC - 4 < math.hypot(u, v) < M.LID_RC + 4)
    if ld < LAND_CHECK:
        ok = False; notes.append(f"underside: {ld:.3f} mm between grooves at {at}")
    land = (ld, f"underside {tuple(round(a, 1) for a in at)}")
    if panels is not None:
        panels.append(("underside (lid flipped)", mid, fr))
    return ok, notes, land

def main():
    want = set(a for a in sys.argv[1:] if not a.startswith("-"))
    truth = json.load(open(os.path.join(HERE, "truth_step.json")))
    parts = {p["id"]: p for p in M.PHANTOMS}
    lids = {l["id"]: l for l in M.LIDS}
    os.makedirs(PREVIEW, exist_ok=True)
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    all_ok = True
    print(f"{'part':5s} {'labels':>6s} {'glyphs':>6s} {'min land':>9s}  result   narrowest at")
    print("-"*60)
    for row in truth:
        if want and row["id"] not in want:
            continue
        shape = load(row["file"])
        panels = []
        if row["part"] == "block":
            p = dict(parts[row["id"]])
            ok, notes, land = check_block(row, p, shape, panels)
            n_g = sum(pieces(l["text"]) for l in row.get("labels", []))
        else:
            ok, notes, land = check_lid(row, lids[row["id"]], shape, panels)
            n_g = sum(pieces(t) for t in M.lid_lines(lids[row["id"]]))
        all_ok &= ok
        print(f"{row['id']:5s} {len(row.get('labels', [])):6d} {n_g:6d} {land[0]:7.3f} mm  "
              f"{'OK  ' if ok else 'FAIL'}   {land[1]}")
        for n in notes:
            print("      ", n)
        # preview
        if panels:
            fig, axs = plt.subplots(len(panels), 1, figsize=(7, 1.2 + 2.4*len(panels)))
            axs = np.atleast_1d(axs)
            for ax, (nm, sec, fr) in zip(axs, panels):
                if nm in ("front", "right", "back", "left"):
                    ext = (-41, 41, -1, (row.get("height_mm") or 10) + 1)
                else:
                    ext = (-41, 41, -41, 41)
                draw(ax, sec, fr, f"{row['id']} {nm} - section {M.ENG/2:g} mm in", ext)
            fig.tight_layout()
            fig.savefig(os.path.join(PREVIEW, f"{row['id']}.png"), dpi=110)
            plt.close(fig)
    print("-"*60)
    print("ALL OK" if all_ok else "SOME FAILED")
    sys.exit(0 if all_ok else 1)

if __name__ == "__main__":
    main()
