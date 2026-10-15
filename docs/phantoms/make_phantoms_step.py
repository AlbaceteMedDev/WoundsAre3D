"""StrataMetric wound phantoms - exact B-rep, exported as STEP AP214.

Replaces the heightfield STL generator. Every cavity is the analytic surface
itself, not a triangulation of it, and the hollow is a true normal offset, so
wall thickness is correct in every direction rather than only in z.
"""
import math, os, sys, json
import numpy as np
import cadquery as cq
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex, BRepBuilderAPI_MakeEdge
from OCP.GeomAPI import GeomAPI_Interpolate
from OCP.TColgp import TColgp_HArray1OfPnt
from OCP.gp import gp_Pnt
from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCP.IFSelect import IFSelect_RetDone
from OCP.Interface import Interface_Static

HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(HERE, "step")
L    = 80.0                 # block side
WALL = 3.5                  # wall thickness, true normal offset
ENG  = 1.0                  # depth of every engraving, on every face
ENG_TOP = ENG_BOT = ENG
KEY_LEN, KEY_Y, KEY_W = 50.0, -30.0, 0.8
TICK_W, TICK_H = 0.8, 6.0
DOT_R, DOT_XY = 1.25, 32.0
# P10 and its lids are keyed: an index groove on P10's top at 3 o'clock (+x, with
# 12 o'clock on the side carrying the part number) and a notch in each lid's rim
# on the side its hole is offset to. Lined up, L2's offset points where its
# clock-position undermining extents assume it does.
INDEX_W, INDEX_LEN, INDEX_GAP = 1.0, 4.0, 0.8
NOTCH_W, NOTCH_D = 1.0, 1.2
MIN_VOID = 4.0              # below this the block stays solid; hollowing buys nothing

# Lettering. Every label is cut as one boolean with all of its glyphs as tools;
# revision B passed each line through as_solid(), which keeps only the largest
# solid of a compound, so each line engraved a single character.
FONT, KIND = "DejaVu Sans Mono", "bold"

def _font_path():
    """The exact face file. Asked for a font it cannot find, OpenCASCADE quietly
    substitutes another, and the layout and letter spacing assume this face's
    metrics - so find the file or stop."""
    cands = [os.environ.get("PHANTOM_FONT"),
             "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
             "/usr/share/fonts/dejavu/DejaVuSansMono-Bold.ttf",
             "/Library/Fonts/DejaVuSansMono-Bold.ttf"]
    try:
        import matplotlib                      # ships the DejaVu faces
        cands.append(os.path.join(matplotlib.get_data_path(), "fonts", "ttf",
                                  "DejaVuSansMono-Bold.ttf"))
    except ImportError:
        pass
    for c in cands:
        if c and os.path.exists(c):
            return c
    raise RuntimeError("DejaVu Sans Mono Bold not found: install fonts-dejavu-core or "
                       "matplotlib, or point PHANTOM_FONT at DejaVuSansMono-Bold.ttf")

FONT_PATH = _font_path()
CAP_RATIO = 0.72            # cap height / font size; the face's is 0.729, so labels
                            # come out about 1 % taller than the cap heights quoted
ADV       = 0.602           # advance / font size; the face is monospaced
CAP_MIN   = 4.5             # smallest cap height whose strokes print as clean grooves
CAP_MAX   = 6.0
PITCH     = 1.4             # baseline-to-baseline / cap height
TRACK     = 0.06            # extra letter spacing / cap height, on every pair
LAND_MIN  = 0.6             # and more where a pair would still leave a thinner ridge
                            # between its grooves (R-A, at 0.02 cap, needs it most)
EDGE      = 1.5             # clearance from a label to any edge or other feature

PHANTOMS = [
    dict(id="P1",  name="hemisphere_r15",        kind="hemisphere", R=15.0, height=19.0),
    dict(id="P2",  name="hemisphere_r25",        kind="hemisphere", R=25.0, height=29.0),
    dict(id="P3",  name="cone_r20_d10",          kind="cone",  R=20.0, h=10.0, height=14.0),
    dict(id="P4",  name="paraboloid_30x20_d12",  kind="paraboloid", a=30.0, b=20.0, h=12.0, height=16.0),
    dict(id="P5",  name="paraboloid_12x8_d4",    kind="paraboloid", a=12.0, b=8.0, h=4.0, height=9.0),
    dict(id="P6",  name="flat_plate",            kind="flat", height=9.0),
    dict(id="P7",  name="lobed_r18_d9",          kind="lobed", R0=18.0, h=9.0, height=13.0,
         lobes=[(3, 0.18, 0.0), (5, 0.10, 0.7)]),
    dict(id="P8",  name="trough_L40_r9_d8",      kind="stadium", R=9.0, seg=40.0, h=8.0, height=12.0),
    dict(id="P9",  name="paraboloid_on_cyl_r60", kind="paraboloid", a=25.0, b=18.0, h=10.0,
         cyl=60.0, key_axis="y", height=22.0),
    dict(id="P10", name="undermining_base",      kind="cylwell", R=20.0, h=12.0,
         pocket_r=28.2, pocket_d=3.0, height=19.0),
]
LIDS = [
    dict(id="L1", name="lid_concentric_r12", R_out=28.0, thick=3.0, hole_r=12.0, hole_cx=0.0),
    dict(id="L2", name="lid_offset6_r12",    R_out=28.0, thick=3.0, hole_r=12.0, hole_cx=6.0),
]

# ------------------------------------------------------------- measurement ---
def volume(shape, tol=1e-8):
    """Volume at a tolerance tight enough to trust; the default is not."""
    g = GProp_GProps(); BRepGProp.VolumeProperties_s(shape.wrapped, g, tol, True)
    return g.Mass()

# ---------------------------------------------------------------- geometry ---
def as_solid(shape):
    """Boolean results come back as compounds; the offset needs a single solid."""
    sl = shape.Solids()
    if len(sl) == 1:
        return sl[0]
    if len(sl) > 1:
        return max(sl, key=lambda s: s.Volume())
    return shape

def _loft(sections, apex=None, ruled=False):
    b = BRepOffsetAPI_ThruSections(True, ruled, 1e-7)
    for w in sections:
        b.AddWire(w.wrapped)
    if apex is not None:
        b.AddVertex(BRepBuilderAPI_MakeVertex(gp_Pnt(*apex)).Vertex())
    b.Build()
    return cq.Shape(b.Shape())

def _spline_wire(pts_xy, z):
    arr = TColgp_HArray1OfPnt(1, len(pts_xy))
    for i, (x, y) in enumerate(pts_xy, start=1):
        arr.SetValue(i, gp_Pnt(float(x), float(y), float(z)))
    it = GeomAPI_Interpolate(arr, True, 1e-9); it.Perform()
    return cq.Wire.assembleEdges([cq.Edge(BRepBuilderAPI_MakeEdge(it.Curve()).Edge())])

def paraboloid(a, b, h, n=48, tmin=0.02):
    """z = -h(1 - x^2/a^2 - y^2/b^2); rim in z=0, apex at z=-h."""
    secs = [cq.Workplane("XY").workplane(offset=-h*(1 - t*t)).ellipse(a*t, b*t).wires().val()
            for t in np.linspace(1.0, tmin, n)]
    return _loft(secs, apex=(0, 0, -h))

def lobed(R0, h, lobes, n=32, npt=240, tmin=0.03):
    secs = []
    for t in np.linspace(1.0, tmin, n):
        th = np.linspace(0, 2*math.pi, npt + 1)[:-1]
        rt = R0*(1 + sum(A*np.cos(m*th + p) for m, A, p in lobes))*t
        secs.append(_spline_wire(list(zip(rt*np.cos(th), rt*np.sin(th))), -h*(1 - t*t)))
    return _loft(secs, apex=(0, 0, -h))

def stadium(R, seg, h, n=48, tmin=0.002):
    """Trough of depth h(1-(d/R)^2), d the distance to the segment |x|<=seg/2.
    Lofted through stadium sections of half-width R*t at z = -h(1-t^2), the
    same parameterisation that makes the paraboloids come out exact. A stadium
    cannot close on a point, so the loft stops at tmin: 0.002 leaves the floor
    0.03 um short of h."""
    secs = []
    for t in np.linspace(1.0, tmin, n):
        w = R*t
        secs.append(cq.Workplane("XY").workplane(offset=-h*(1 - t*t))
                      .slot2D(seg + 2*w, 2*w, 0).wires().val())
    return as_solid(_loft(secs))

def cavity(p):
    k = p["kind"]
    if k == "hemisphere": return cq.Workplane("XY").sphere(p["R"]).val()
    if k == "cone":       return cq.Solid.makeCone(0.0, p["R"], p["h"],
                                                   cq.Vector(0, 0, -p["h"]), cq.Vector(0, 0, 1))
    if k == "paraboloid": return paraboloid(p["a"], p["b"], p["h"])
    if k == "lobed":      return lobed(p["R0"], p["h"], p["lobes"])
    if k == "stadium":    return stadium(p["R"], p["seg"], p["h"])
    if k == "cylwell":
        pk   = cq.Workplane("XY").circle(p["pocket_r"]).extrude(-p["pocket_d"]).val()
        well = (cq.Workplane("XY").workplane(offset=-p["pocket_d"])
                  .circle(p["R"]).extrude(-p["h"]).val())
        return pk.fuse(well)
    return None

def analytic(p):
    k = p["kind"]
    if k == "hemisphere":
        R = p["R"]; return 2/3*math.pi*R**3, math.pi*R*R, R
    if k == "cone":
        R, h = p["R"], p["h"]; return math.pi*R*R*h/3, math.pi*R*R, h
    if k == "paraboloid":
        a, b, h = p["a"], p["b"], p["h"]; return math.pi*a*b*h/2, math.pi*a*b, h
    if k == "lobed":
        R0, h = p["R0"], p["h"]; s2 = sum(A*A for _, A, _ in p["lobes"])
        return math.pi*h*R0*R0/4*(2 + s2), math.pi*R0*R0/2*(2 + s2), h
    if k == "stadium":
        R, Ls, h = p["R"], p["seg"], p["h"]
        return 4*h*R*Ls/3 + math.pi*h*R*R/2, 2*R*Ls + math.pi*R*R, h
    if k == "cylwell":
        R, h = p["R"], p["h"]; return math.pi*R*R*h, math.pi*R*R, h
    return 0.0, 0.0, 0.0

# ------------------------------------------------------------------ blocks ---
def block(p):
    """Solid block, bottom face on z=0, top at z=height (or a cylinder of
    radius cyl about the y axis, for the curved-limb phantom)."""
    H = p["height"]
    b = cq.Workplane("XY").box(L, L, H, centered=(True, True, False)).val()
    Rc = p.get("cyl")
    if Rc:
        cyl = (cq.Workplane("XZ").workplane(offset=-(L/2 + 5))
                 .circle(Rc).extrude(L + 10).val().translate((0, 0, H - Rc)))
        b = b.intersect(cyl)
    return b

def base_z(p, x):
    Rc = p.get("cyl")
    if not Rc:
        return p["height"]
    return p["height"] - Rc + math.sqrt(max(Rc*Rc - x*x, 0.0))

def placed_cavity(p):
    """Cavity solid positioned in the block. On a curved top the cavity is
    sheared vertically so its depth is measured from the local surface."""
    cav = cavity(p)
    if cav is None:
        return None
    if not p.get("cyl"):
        return cav.translate((0, 0, p["height"]))
    a, b, h = p["a"], p["b"], p["h"]                      # only the curved one
    # The rim follows the curved top, so a loft through depth-parallel sections
    # would have a non-planar end that ThruSections cannot cap. Section it along
    # x instead: every slice at constant x is planar, bounded above by the chord
    # z = base(x) and below by a parabola.
    from OCP.TColStd import TColStd_HArray1OfReal
    NP = 61
    par = TColStd_HArray1OfReal(1, NP)
    for i, u in enumerate(np.linspace(0.0, 1.0, NP), start=1):
        par.SetValue(i, float(u))
    secs, n = [], 72
    # cosine spacing crowds slices into the tips, where the flat end caps would
    # otherwise truncate the most
    for xi in (-a*np.cos(np.linspace(0.0, math.pi, n)))[1:-1]:
        f = (xi/a)**2
        yy = b*math.sqrt(max(1.0 - f, 0.0))
        zt = base_z(p, float(xi))
        # every slice gets the same NP points and the same parameters; left to
        # chord length, each slice's knots differ and the loft merges them all
        # into one surface of millions of poles
        ys = -yy*np.cos(np.linspace(0.0, math.pi, NP))
        pts = [(float(y), float(zt - h*(1.0 - f - (y/b)**2))) for y in ys]
        arr = TColgp_HArray1OfPnt(1, len(pts))
        for i, (y, z) in enumerate(pts, start=1):
            arr.SetValue(i, gp_Pnt(float(xi), y, z))
        it = GeomAPI_Interpolate(arr, par, False, 1e-9); it.Perform()
        e = cq.Edge(BRepBuilderAPI_MakeEdge(it.Curve()).Edge())
        ln = cq.Edge.makeLine(cq.Vector(float(xi), pts[-1][0], pts[-1][1]),
                              cq.Vector(float(xi), pts[0][0], pts[0][1]))
        secs.append(cq.Wire.assembleEdges([e, ln]))
    bb = BRepOffsetAPI_ThruSections(True, False, 1e-7)
    for w in secs:
        bb.AddWire(w.wrapped)
    bb.Build()
    return as_solid(cq.Shape(bb.Shape()))

def top_skin(solid, depth, p=None):
    """The top `depth` of the solid, measured along the surface normal. On a flat
    top that is a vertical offset; on the curved-limb phantom's cylindrical top
    a vertical offset would leave only depth*cos(slope) along the normal - 0.85 mm
    at the fiducial dots - so there it is the shell outside a coaxial cylinder."""
    if p is not None and p.get("cyl"):
        Rc, H = p["cyl"], p["height"]
        core = (cq.Workplane("XZ").workplane(offset=-(L/2 + 5))
                  .circle(Rc - depth).extrude(L + 10).val().translate((0, 0, H - Rc)))
        return solid.cut(core)
    return solid.cut(solid.translate((0, 0, -depth)))

def bottom_skin(solid, depth):
    return solid.cut(solid.translate((0, 0, depth)))

# -------------------------------------------------------------- engravings ---
def top_tools(p):
    """Prisms for the key line, its end ticks, the fiducial dots and the id."""
    H = p["height"] + 10.0
    tools = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            tools.append(cq.Workplane("XY").center(sx*DOT_XY, sy*DOT_XY)
                           .circle(DOT_R).extrude(H).val())
    half = KEY_LEN/2.0
    if p.get("key_axis") == "y":
        groove = cq.Workplane("XY").center(KEY_Y, 0.0).box(KEY_W, KEY_LEN, H,
                                                           centered=(True, True, False)).val()
        ticks = [cq.Workplane("XY").center(KEY_Y, sy*half)
                   .box(TICK_H, TICK_W, H, centered=(True, True, False)).val() for sy in (-1, 1)]
    else:
        groove = cq.Workplane("XY").center(0.0, KEY_Y).box(KEY_LEN, KEY_W, H,
                                                           centered=(True, True, False)).val()
        ticks = [cq.Workplane("XY").center(sx*half, KEY_Y)
                   .box(TICK_W, TICK_H, H, centered=(True, True, False)).val() for sx in (-1, 1)]
    if p["kind"] == "cylwell":
        r0 = p["pocket_r"] + INDEX_GAP
        tools.append(cq.Workplane("XY").center(r0 + INDEX_LEN/2, 0.0)
                       .box(INDEX_LEN, INDEX_W, H, centered=(True, True, False)).val())
    return tools + [groove] + ticks

def _gap(a, b):
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    d = BRepExtrema_DistShapeShape(cq.Compound.makeCompound(a).wrapped,
                                   cq.Compound.makeCompound(b).wrapped)
    d.Perform()
    return d.Value()

def tracked(line, txt, cap, origin, xdir, land=LAND_MIN):
    """Open up the letter spacing of a line built by cadquery, which sets the
    font's own advance and has no tracking control. Each glyph solid is moved
    along the line by TRACK*cap per character cell before it, keeping its own
    place on the baseline; then any neighbouring pair whose grooves would still
    stand closer than `land` is pushed apart until they don't. The line stays
    centred."""
    n = len(txt)
    adv = ADV*cap/CAP_RATIO
    xd = cq.Vector(*xdir).normalized()
    o = cq.Vector(*origin)
    u0 = -n*adv/2
    cells = {}
    for g in (line.Solids() or [line]):
        u = (g.Center() - o).dot(xd)
        cells.setdefault(min(n - 1, max(0, int((u - u0)//adv))), []).append(g)
    placed, extra, prev = [], 0.0, None
    for cell, gs in sorted(cells.items()):
        if txt[cell] == "0" and len(gs) > 1:
            # this face's zero is dotted; engraved, the ridge between dot and ring
            # is 0.05 cap - 0.2 mm - and would not print. A plain ring reads as 0.
            gs = [max(gs, key=lambda s: s.Volume())]
        grp = [g.translate(xd*(TRACK*cap*(cell - (n - 1)/2) + extra)) for g in gs]
        if prev is not None and prev[0] == cell - 1:
            d = _gap(prev[1], grp)
            if d < land:
                extra += land - d
                grp = [g.translate(xd*(land - d)) for g in grp]
        placed.append((cell, grp))
        prev = (cell, grp)
    return cq.Compound.makeCompound([g.translate(xd*(-extra/2)) for _, grp in placed for g in grp])

def text_prism(txt, cap, x, y, z0, height, angle=0.0):
    """Text standing up from z0, for cutting into a top face of any shape by
    intersecting it with that face's skin; turned `angle` degrees about z."""
    line = (cq.Workplane("XY").workplane(offset=z0)
              .text(txt, cap/CAP_RATIO, height, combine=False, font=FONT, fontPath=FONT_PATH, kind=KIND,
                    halign="center", valign="center").val())
    t = tracked(line, txt, cap, (0, 0, z0), (1, 0, 0))
    if angle:
        t = t.rotate((0, 0, 0), (0, 0, 1), angle)
    return t.translate((x, y, 0))

def key_label(p):
    """Where the key line's '50.000' goes: between the key and the nearest edge,
    tops towards the key, readable from that edge. P9's key runs along y, so its
    label stands beside it rather than under the cavity, whose opening happens to
    be 50 mm across."""
    if p.get("key_axis") == "y":
        return dict(x=KEY_Y - 6.0, y=0.0, angle=-90.0)
    return dict(x=0.0, y=KEY_Y - 6.0, angle=0.0)

def text_on(txt, cap, at, xdir, normal, depth=ENG, land=LAND_MIN):
    """Engraving tool for one line of text on a planar face. `at` is the point on
    the face the line is centred on and `normal` the face's outward normal; the
    prism runs from `depth` inside the face to 1 mm outside it, and reads the
    right way round to someone looking at that face."""
    n = cq.Vector(*normal)
    o = cq.Vector(*at) - n*depth
    pl = cq.Plane(origin=o.toTuple(), xDir=xdir, normal=normal)
    line = (cq.Workplane(pl).text(txt, cap/CAP_RATIO, depth + 1.0, combine=False,
                                  font=FONT, fontPath=FONT_PATH, kind=KIND,
                                  halign="center", valign="center")
              .val())
    return tracked(line, txt, cap, o.toTuple(), xdir, land)

def text_len(s, cap):
    return len(s)*ADV*cap/CAP_RATIO + (len(s) - 1)*TRACK*cap

def cut_all(body, tools, fuzzy=(0.0, 1e-5, 1e-4)):
    """Cut every solid of every tool from `body` in one boolean. The result must
    still be one solid: an engraving that detached a piece would show up here."""
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.TopTools import TopTools_ListOfShape
    solids = [s for t in tools for s in (t.Solids() or [t])]
    if not solids:
        return body
    for f in fuzzy:
        op = BRepAlgoAPI_Cut()
        la = TopTools_ListOfShape(); la.Append(as_solid(body).wrapped)
        lb = TopTools_ListOfShape()
        for s in solids:
            lb.Append(s.wrapped)
        op.SetArguments(la); op.SetTools(lb)
        if f:
            op.SetFuzzyValue(f)
        op.Build()
        if not op.IsDone():
            continue
        r = cq.Shape.cast(op.Shape())
        if r is not None and len(r.Solids()) == 1:
            return r.Solids()[0]
    raise RuntimeError("engraving cut failed or split the part")

# ------------------------------------------------------------------ labels ---
SHAPE = {"hemisphere": "HEMISPHERE", "cone": "CONE", "paraboloid": "PARABOLOID",
         "lobed": "LOBED", "stadium": "TROUGH", "cylwell": "UNDERMINING",
         "flat": "FLAT PLATE"}

def dims(p):
    k = p["kind"]
    if k in ("hemisphere", "cone"): return f"R{p['R']:g}"
    if k == "paraboloid":           return f"{2*p['a']:g}x{2*p['b']:g}"     # the opening
    if k == "lobed":                return f"R{p['R0']:g}"
    if k == "stadium":              return f"{p['seg'] + 2*p['R']:g}x{2*p['R']:g}"
    if k == "cylwell":              return f"R{p['R']:g}"
    return ""

def skin_area(p, n=20001):
    """Area of a cavity's opening measured on the skin itself rather than in plan.
    Only the curved-limb phantom differs: there the skin is a cylinder about y,
    which stretches the plan area by Rc/sqrt(Rc^2 - x^2)."""
    vol, ar, dep = analytic(p)
    Rc = p.get("cyl")
    if not Rc:
        return ar
    a, b = p["a"], p["b"]
    x = np.linspace(-a, a, n)
    f = 2*b*np.sqrt(np.clip(1 - (x/a)**2, 0, None))*Rc/np.sqrt(Rc*Rc - x*x)
    return float(np.sum((f[1:] + f[:-1])/2*np.diff(x)))

def extents(p, l):
    """Undermining extent at each clock position, 12 o'clock first: from the wound
    edge outward to the chamber wall, with the lid's offset at 3 o'clock (+x)."""
    R, r, c = p["R"], l["hole_r"], l["hole_cx"]
    out = []
    for k in range(12):
        th = math.radians(90.0 - 30.0*k)
        s = -c*math.cos(th) + math.sqrt((c*math.cos(th))**2 + R*R - c*c)
        out.append(s - r)
    return out

def assembled(p, l):
    """P10 with a lid seated: the wound a scanner and a probe actually meet. The
    lid's top is flush with the block's, so depth runs from that skin plane to
    the chamber floor; what lies under the lid's shelf is hidden."""
    R, h, r, t = p["R"], p["h"], l["hole_r"], l["thick"]
    return dict(depth=t + h, area=math.pi*r*r,
                volume=math.pi*r*r*t + math.pi*R*R*h,
                visible=math.pi*r*r*(t + h),
                hidden=math.pi*(R*R - r*r)*h,
                undermined_area=math.pi*(R*R - r*r))

def side_lines(p, short=False):
    """What the side walls say: which part, then its three ground-truth numbers.
    short drops the dimensions from the first line, for walls too low to take it
    (they are on the underside regardless)."""
    if p["kind"] == "cylwell":
        a = assembled(p, LIDS[0])
        return [f"{p['id']} UNDERMINING", "LID NOTCH TO MARK", f"DEPTH {a['depth']:.3f} MM",
                f"AREA {a['area']:.2f} MM2", f"VOL {a['volume']:.2f} MM3",
                f"SEEN {a['visible']:.2f} MM3", f"HIDDEN {a['hidden']:.2f} MM3",
                f"UM AREA {a['undermined_area']:.2f} MM2"]
    vol, ar, dep = analytic(p)
    head = f"{p['id']} {SHAPE[p['kind']]}" + ("" if short else f" {dims(p)}")
    area = f"PLAN {ar:.2f} MM2" if p.get("cyl") else f"AREA {ar:.2f} MM2"
    return [head.strip(), f"DEPTH {dep:.3f} MM", area, f"VOL {vol:.2f} MM3"]

def bottom_lines(p):
    """The underside carries the full specification."""
    vol, ar, dep = analytic(p)
    k = p["kind"]
    geom = {"hemisphere": [f"SPHERE R {p.get('R', 0):.3f}"],
            "cone":       [f"BASE R {p.get('R', 0):.3f}"],
            "paraboloid": [f"A {p.get('a', 0):.3f} B {p.get('b', 0):.3f}"],
            "lobed":      [f"R0 {p['R0']:.3f}",
                           "LOBES " + " ".join(f"{m}:{A:.2f}".replace(":0.", ":.")
                                               for m, A, _ in p["lobes"])]
                          + [f"{m}-LOBE PHASE {ph:g}" for m, _, ph in p["lobes"] if ph]
                          if k == "lobed" else [],
            "stadium":    [f"L {p.get('seg', 0):.3f} R {p.get('R', 0):.3f}"],
            "cylwell":    [f"WELL R {p.get('R', 0):.3f}"]}.get(k, [])
    lines = [f"STRATAMETRIC {p['id']}", SHAPE[p["kind"]]] + geom
    if k == "cylwell":
        # assembled values; the long lines are kept off the two ends of the block,
        # which run past the floor vents
        a = assembled(p, LIDS[0])
        return lines + [f"WELL DEPTH {p['h']:.3f}", f"SEAT R {p['pocket_r']:.3f}",
                        f"SEAT DEPTH {p['pocket_d']:.3f}", "WITH LID L1/L2:",
                        f"DEPTH {a['depth']:.3f} MM", f"AREA {a['area']:.2f} MM2",
                        f"HIDDEN {a['hidden']:.2f} MM3", f"VOL {a['volume']:.2f} MM3"]
    elif p.get("cyl"):
        lines += [f"DEPTH {dep:.3f} MM", f"PLAN {ar:.2f} MM2", f"SKIN {skin_area(p):.2f} MM2",
                  f"VOL {vol:.2f} MM3", f"TOP CYL R {p['cyl']:.3f}"]
    else:
        lines += [f"DEPTH {dep:.3f} MM", f"AREA {ar:.2f} MM2", f"VOL {vol:.2f} MM3"]
    lines += [f"BLOCK 80x80x{p['height']:g}"]
    return lines

SIDES = [("front", (0, -1, 0), (1, 0, 0)),          # name, outward normal, reading direction
         ("right", (1, 0, 0), (0, 1, 0)),
         ("back",  (0, 1, 0), (-1, 0, 0)),
         ("left",  (-1, 0, 0), (0, -1, 0))]

def side_room(p, side):
    """Half-length a centred label may take on a side face, and the height of the
    face's top edge as a function of that half-length."""
    half = L/2 - EDGE
    if side[0] in ("front", "back"):
        return half, lambda hl: base_z(p, hl)      # base_z falls away from x = 0
    return half, lambda hl: base_z(p, L/2)

def stack(lines, cap, half, top):
    """Baseline-centre heights for `lines`, top line first, or None if they do
    not fit. Each line is checked against the face's top edge over its own
    length, so on a curved face a long line can sit under a short one; any room
    left over is split above and below."""
    pitch = PITCH*cap
    hls = [text_len(s, cap)/2 for s in lines]
    if max(hls) > half:
        return None
    n = len(lines)
    zs = [EDGE + cap/2 + (n - 1 - j)*pitch for j in range(n)]       # packed to the floor
    slack = min(top(hl) - EDGE - (z + cap/2) for z, hl in zip(zs, hls))
    if slack < 0:
        return None
    return [z + slack/2 for z in zs]

def fit_cap(lines, half, top):
    cap = CAP_MAX
    while cap >= CAP_MIN - 1e-9:
        if stack(lines, cap, half, top) is not None:
            return round(cap, 2)
        cap -= 0.05
    return None

def splits(n, faces=4, most=3):
    if faces == 0:
        if n == 0:
            yield ()
        return
    for k in range(min(n, most) + 1):
        for rest in splits(n - k, faces - 1, most):
            yield (k,) + rest

FACE_PREF = {"front": 8, "back": 4, "right": 2, "left": 1}

def layout_sides(p):
    """Spread the side lines over the four walls at the largest cap height every
    wall can take. The part's name comes first, on the front wall when it can;
    the three measurements follow in their usual order unless a curved wall
    needs them reordered to fit. Ties go to fewer walls, then to the front and
    back."""
    import itertools
    best = None
    for short in (False, True):
        lines = side_lines(p, short)
        head, meas = lines[:1], lines[1:]
        for rank, perm in enumerate(itertools.permutations(meas)):
            cand = _layout_sides(p, head + list(perm))
            if cand is None:
                continue
            key = cand[0] + (-rank,)
            if best is None or key > best[0]:
                best = (key,) + cand[1:]
        if best is not None:
            break
    if best is None:
        raise RuntimeError(f"{p['id']}: side labels do not fit at {CAP_MIN} mm cap height")
    return _place_sides(p, best)

def _layout_sides(p, lines):
    best = None
    for sp in splits(len(lines)):
        caps, groups, i = [], [], 0
        for side, k in zip(SIDES, sp):
            if not k:
                continue
            grp = lines[i:i + k]; i += k
            c = fit_cap(grp, *side_room(p, side))
            if c is None:
                caps = None; break
            caps.append(c); groups.append((side, grp))
        if not caps:
            continue
        pref = sum(FACE_PREF[g[0][0]] for g in groups) + (16 if groups[0][0][0] == "front" else 0)
        key = (min(caps), -len(groups), -max(sp), pref)
        if best is None or key > best[0]:
            best = (key, min(caps), groups)
    return best

def _place_sides(p, best):
    cap, plan = best[1], []
    for side, grp in best[2]:
        name, n, xd = side
        zs = stack(grp, cap, *side_room(p, side))
        for s, z in zip(grp, zs):
            at = (n[0]*L/2, n[1]*L/2, z)
            plan.append(dict(face=name, text=s, cap=cap, at=at, xdir=xd, normal=n))
    return plan

def layout_bottom(p, keepouts):
    """The specification block, centred on the underside and read from below, at
    the largest cap that clears the edges. A line that would run into a vent is
    slid sideways by the least amount that clears it."""
    lines = bottom_lines(p)

    def clear(x0, yw, hw, hh):
        for (cx, cy, r) in keepouts:                       # rectangle vs circle
            dx = max(abs(cx - x0) - hw, 0.0)
            dy = max(abs(cy - yw) - hh, 0.0)
            if math.hypot(dx, dy) < r + EDGE:
                return False
        return True

    cap = CAP_MAX
    while cap >= CAP_MIN - 1e-9:
        pitch = PITCH*cap
        rows = []
        if cap + pitch*(len(lines) - 1) + 2*EDGE <= L:
            for j, s in enumerate(lines):
                yw = -((len(lines) - 1)*pitch/2 - j*pitch)    # first line is up, seen from below
                hw = text_len(s, cap)/2
                room = L/2 - EDGE - hw
                if room < 0:
                    break
                shifts = sorted(np.arange(-room, room + 1e-9, 0.25), key=abs)
                x0 = next((x for x in [0.0] + shifts if clear(x, yw, hw, cap/2)), None)
                if x0 is None:
                    break
                rows.append(dict(face="bottom", text=s, cap=round(cap, 2),
                                 at=(round(float(x0), 3), yw, 0.0),
                                 xdir=(1, 0, 0), normal=(0, 0, -1)))
        if len(rows) == len(lines):
            return rows
        cap -= 0.05
    raise RuntimeError(f"{p['id']}: bottom specification does not fit at {CAP_MIN} mm")

def label_tools(plan):
    return [text_on(r["text"], r["cap"], r["at"], r["xdir"], r["normal"]) for r in plan]

def arc_text(txt, cap, rc, outer, depth=ENG):
    """A line on the underside of a lid, bent round an arc of radius rc about the
    lid axis and read from below. Each glyph keeps its place on the straight
    line's baseline and is swung onto the arc. outer=True runs round the far
    side with the letters' tops outward; False round the near side, tops inward."""
    y0 = -rc if outer else rc
    sign = 1 if outer else -1
    line = text_on(txt, cap, (0.0, y0, 0.0), (1, 0, 0), (0, 0, -1), depth)
    pieces = sorted(((0.5*(g.BoundingBox().xmin + g.BoundingBox().xmax), g)
                     for g in line.Solids()), key=lambda t: t[0])
    # Bending brings the glyphs' inner ends closer together than on the straight
    # line, so the spacing is checked again on the arc and opened where needed.
    out, extra = [], 0.0
    for xk, g in pieces:
        bent = g.translate((-xk, 0, 0)).rotate((0, 0, 0), (0, 0, 1),
                                                math.degrees(xk/rc)*sign + extra)
        if out:
            d = _gap([out[-1]], [bent])
            if d < LAND_MIN:
                da = math.degrees((LAND_MIN - d)/(rc - cap/2))*1.05*sign
                extra += da
                bent = bent.rotate((0, 0, 0), (0, 0, 1), da)
        out.append(bent)
    return [b.rotate((0, 0, 0), (0, 0, 1), -extra/2) for b in out]

# ------------------------------------------------------------------ hollow ---
def Rc_depth(p):
    """How far the curved top dips below its crown at the block edge."""
    Rc = p.get("cyl")
    return 0.0 if not Rc else Rc - math.sqrt(max(Rc*Rc - (L/2)**2, 0.0))

def grown_cavity(p, w=WALL):
    """The cavity enlarged so that every point of its surface is at least `w`
    inside it, built analytically. A surface of slope s needs a horizontal
    enlargement of w*sqrt(1+s^2) to clear it by w measured perpendicular, so
    each shape is grown by its own worst-case slope. Conservative, which only
    ever costs material - never wall."""
    H = p["height"]; k = p["kind"]
    if k == "hemisphere":
        R = p["R"]
        return cq.Workplane("XY").workplane(offset=H).sphere(R + w).val()
    if k == "cone":
        R, h = p["R"], p["h"]
        sl = h/R; k = math.sqrt(1 + sl*sl)
        d, rr = h + w*k, R + w*k/sl                # parallel offset: same slope
        return cq.Solid.makeCone(0.0, rr, d, cq.Vector(0, 0, H - d), cq.Vector(0, 0, 1))
    if k == "paraboloid":
        a, b, h = p["a"], p["b"], p["h"]
        sa, sb = 2*h/a, 2*h/b
        lean = abs(a*a - b*b)/(2*a*b)
        fl = math.sqrt(1 + lean*lean)
        ga = w*math.sqrt(1 + sa*sa)/sa*fl; gb = w*math.sqrt(1 + sb*sb)/sb*fl
        g = max(ga, gb)
        if p.get("cyl"):
            # curved top: a vertical elliptic prism, conservative but robust
            return (cq.Workplane("XY").workplane(offset=H - Rc_depth(p) - h - w)
                      .ellipse(a + g, b + g).extrude(200.0).val())
        return paraboloid(a + ga, b + gb, h + w).translate((0, 0, H))
    if k == "lobed":
        R0, h, lb = p["R0"], p["h"], p["lobes"]
        th = np.linspace(0, 2*math.pi, 2001)
        rt = R0*(1 + sum(A*np.cos(m*th + q) for m, A, q in lb))
        drt = R0*sum(-A*m*np.sin(m*th + q) for m, A, q in lb)
        lean = float(np.max(np.abs(drt/rt)))            # tan of the worst normal lean
        s = 2*h/float(rt.max())                           # shallowest rim slope
        g = w*math.sqrt(1 + s*s)/s*math.sqrt(1 + lean*lean)
        return lobed_grown(R0, h + w, lb, g).translate((0, 0, H))
    if k == "stadium":
        R, seg, h = p["R"], p["seg"], p["h"]
        s = 2*h/R; g = w*math.sqrt(1 + s*s)
        length = seg + 2*(R + g)
        if (L/2 - WALL) - length/2 < 1.0:
            # its ends would stop 0.36 mm short of the void's end walls: a slit too
            # narrow to clear of powder. Run them through instead; the void splits
            # into two halves, each with its own vent.
            length = 2*(L/2 - WALL + 1.0)
        return (cq.Workplane("XY").workplane(offset=H - h - w)
                  .slot2D(length, 2*(R + g), 0).extrude(h + w + 1).val())
    if k == "cylwell":
        R, h, pr, pd = p["R"], p["h"], p["pocket_r"], p["pocket_d"]
        well = (cq.Workplane("XY").workplane(offset=H - pd - h - w)
                  .circle(R + w).extrude(pd + h + w + 1).val())
        pk = (cq.Workplane("XY").workplane(offset=H - pd - w)
                .circle(pr + w).extrude(pd + w + 1).val())
        return well.fuse(pk)
    return None

def lobed_grown(R0, h, lobes, g, n=32, npt=240, tmin=0.03):
    """Lobed paraboloid whose rim radius is r(theta)+g at every angle."""
    secs = []
    for t in np.linspace(1.0, tmin, n):
        th = np.linspace(0, 2*math.pi, npt + 1)[:-1]
        rt = (R0*(1 + sum(A*np.cos(m*th + q) for m, A, q in lobes)) + g)*t
        secs.append(_spline_wire(list(zip(rt*np.cos(th), rt*np.sin(th))), -h*(1 - t*t)))
    return _loft(secs, apex=(0, 0, -h))

def safe_cut(a, b, fuzzy=(0.0, 1e-5, 1e-4, 1e-3), keep_all=False):
    """Boolean cut that retries with a fuzzy tolerance; OCC returns a null shape
    rather than raising when two surfaces meet within its default tolerance.
    Returns the largest solid of the result unless keep_all."""
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.TopTools import TopTools_ListOfShape
    for f in fuzzy:
        try:
            op = BRepAlgoAPI_Cut()
            la = TopTools_ListOfShape(); la.Append(as_solid(a).wrapped)
            lb = TopTools_ListOfShape(); lb.Append(as_solid(b).wrapped)
            op.SetArguments(la); op.SetTools(lb)
            if f: op.SetFuzzyValue(f)
            op.Build()
            if not op.IsDone():
                continue
            r = cq.Shape.cast(op.Shape())
            if r is not None and r.Solids():
                return r if keep_all else as_solid(r)
        except Exception:
            continue
    raise RuntimeError("cut failed at every fuzzy tolerance")

def void_solid(p, wall=WALL):
    """The enclosed void: `wall` inside the sides and floor, `wall` below the top
    surface, and clear of the grown cavity."""
    H = p["height"]
    inset = (cq.Workplane("XY").workplane(offset=wall)
               .box(L - 2*wall, L - 2*wall, H, centered=(True, True, False)).val())
    Rc = p.get("cyl")
    if Rc:
        cap = (cq.Workplane("XZ").workplane(offset=-(L/2 + 5))
                 .circle(Rc - wall).extrude(L + 10).val().translate((0, 0, H - Rc)))
        v = as_solid(inset.intersect(cap))
    else:
        v = as_solid(inset.intersect(block(p).translate((0, 0, -wall))))
    gc = grown_cavity(p, wall)
    if gc is not None:
        # Clip the grown cavity to the void's own z band first: leaving its deep
        # apex in the boolean is what makes the kernel return a null shape.
        bb = v.BoundingBox()
        band = (cq.Workplane("XY").workplane(offset=bb.zmin - 1.0)
                  .box(4*L, 4*L, (bb.zmax - bb.zmin) + 2.0,
                       centered=(True, True, False)).val())
        gc = as_solid(gc.intersect(band)).clean()
        v = safe_cut(v, gc, keep_all=True)
    # keep every part of the void a floor vent reaches; anything else stays solid
    sl = [s for s in v.Solids()
          if any(volume(vent_hole(x, y).intersect(s)) > 1.0 for (x, y) in BOTTOM_VENTS)]
    if not sl:
        return None
    return sl[0].clean() if len(sl) == 1 else cq.Compound.makeCompound([s.clean() for s in sl])

BOTTOM_VENTS = [(33.0, 33.0), (-33.0, -33.0)]
BOTTOM_VENT_DIA = 6.0

def vent_hole(x, y):
    return (cq.Workplane("XY").workplane(offset=-1.0).center(x, y)
              .circle(BOTTOM_VENT_DIA/2).extrude(1.0 + WALL + 0.5).val())

def bottom_vents(p, void):
    """Powder escape holes up through the floor at two opposite corners, where
    every block's void runs clear of the cavity's grown footprint. Revision B ran
    them along x through the side walls at the void's mid-height: on the
    curved-limb block, whose +-X walls are only 6.7 mm tall, they came out through
    the top face instead, as open slots that took the fiducial dots with them;
    on the shallow blocks the void's height capped them at 4-6 mm; and they
    pinched the side walls the labels now use. Through the floor none of that
    applies, and they show on no face but the base."""
    out = []
    for (x, y) in BOTTOM_VENTS:
        hole = vent_hole(x, y)
        if volume(hole.intersect(void)) < 0.25*math.pi*(BOTTOM_VENT_DIA/2)**2:
            raise RuntimeError(f"{p['id']}: floor vent at {(x, y)} does not reach the void")
        out.append(hole)
    return out

# -------------------------------------------------------------------- lids ---
LID_RC, LID_CAP = 24.0, 4.5     # label radius on the lid underside, and its cap height

def lid_lines(l):
    return [f"{l['id']} HOLE D{2*l['hole_r']:.3f}", f"OFFSET {l['hole_cx']:.3f} MM"]

def lid(l, with_text=True, notch=True):
    """The lid's top face is skin around the wound opening, so it stays clean.
    Its label goes on the underside, in the ring that rests on P10's pocket floor,
    outside the chamber: nothing there is seen by the sensor or changes the
    undermined volume. The rim notch at +x, the side the hole is offset to, lines
    up with P10's index groove."""
    d = (cq.Workplane("XY").circle(l["R_out"]).extrude(l["thick"])
           .faces(">Z").workplane().center(l["hole_cx"], 0).circle(l["hole_r"])
           .cutThruAll()).val()
    if notch:
        cut = (cq.Workplane("XY").workplane(offset=-1.0)
                 .center(l["R_out"] - NOTCH_D + (NOTCH_D + 1.0)/2, 0.0)
                 .box(NOTCH_D + 1.0, NOTCH_W, l["thick"] + 2.0, centered=(True, True, False)).val())
        d = cut_all(d, [cut])
    if not with_text:
        return d
    a, b = lid_lines(l)
    return cut_all(d, arc_text(a, LID_CAP, LID_RC, True) + arc_text(b, LID_CAP, LID_RC, False))

# -------------------------------------------------------------------- step ---
def write_step(shape, path, name):
    # The writer sets up the STEP controller and its defaults, so it comes first:
    # settings made before the first writer exists are lost. Schema 4 is AP214
    # (IS); 3, which revision B used, is AP203.
    w = STEPControl_Writer()
    Interface_Static.SetIVal_s("write.step.schema", 4)
    Interface_Static.SetCVal_s("write.step.product.name", name)
    w.Model(True)
    w.Transfer(shape.wrapped, STEPControl_AsIs)
    if w.Write(path) != IFSelect_RetDone:
        raise RuntimeError(f"STEP write failed for {path}")

# -------------------------------------------------------------------- main ---
def build(p, with_text=True, hollow=True):
    """The finished part. hollow=False gives the same part, engraved, without the
    void or the vents: what the wall check measures the void against."""
    blk = block(p)
    solid_block_vol = volume(blk)
    cav = placed_cavity(p)
    body = as_solid(blk.cut(cav)) if cav is not None else as_solid(blk)
    cav_vol = solid_block_vol - volume(body)
    if p["kind"] == "cylwell":
        cav_vol -= math.pi*p["pocket_r"]**2*p["pocket_d"]

    # The top skin is taken from the un-engraved block, so engravings follow the
    # top's own shape and never take part in the hollowing offset.
    tskin = top_skin(blk, ENG, p)

    body = as_solid(body).clean()
    v = void_solid(p)
    ve = None
    if v is not None and volume(v) > 1000.0:
        bb = v.BoundingBox(); ve = (bb.zmin, bb.zmax)
    hollowed = bool(ve and (ve[1] - ve[0]) >= MIN_VOID and p["height"] >= 12.0)
    vent, keepouts = None, []
    if hollowed:
        vts = bottom_vents(p, v)
        vent = dict(axis="z", dia=BOTTOM_VENT_DIA, count=len(vts))
        keepouts = [(x, y, BOTTOM_VENT_DIA/2) for (x, y) in BOTTOM_VENTS]
        if hollow:
            body = cut_all(as_solid(body.cut(v)), vts)

    # top-face text runs from below the lowest point of the top to above its
    # highest, and the skin takes it to depth - wherever on a curved top it sits
    z0 = base_z(p, L/2) - ENG - 2.0
    zh = p["height"] - z0 + 5.0
    tools = [t.intersect(tskin) for t in top_tools(p)]
    tools.append(text_prism(p["id"], 6.0, 0.0, 33.0, z0, zh).intersect(tskin))
    k = key_label(p)
    tools.append(text_prism(f"{KEY_LEN:.3f}", CAP_MIN, k["x"], k["y"], z0, zh,
                            k["angle"]).intersect(tskin))
    plan = []
    if with_text:
        plan = layout_sides(p) + layout_bottom(p, keepouts)
        tools += label_tools(plan)
    body = cut_all(body, tools)
    return body, cav_vol, solid_block_vol, hollowed, plan, vent

def main():
    os.makedirs(OUT, exist_ok=True)
    want = set(a for a in sys.argv[1:] if not a.startswith("-"))
    no_text = "--no-text" in sys.argv
    truth_path = os.path.join(HERE, "truth_step.json")
    old = {}
    if want and os.path.exists(truth_path):          # a partial run keeps the other rows
        old = {r["id"]: r for r in json.load(open(truth_path))}
    rows, total = {}, 0.0
    print(f"{'file':34s} {'H':>4s} {'V_true':>11s} {'B-rep':>11s} {'err':>10s} "
          f"{'material':>10s}  hollow  label cap")
    print("-"*108)
    for p in PHANTOMS:
        if want and p["id"] not in want:
            continue
        s, cav_vol, blk_vol, hol, plan, vent = build(p, with_text=not no_text)
        v_true, ar, dep = analytic(p)
        err = 0.0 if v_true == 0 else abs(cav_vol - v_true)/v_true*100
        mat = volume(s)
        total += mat
        fn = f"{p['id']}_{p['name']}.step"
        assert err < 0.01, f"{p['id']} cavity volume off by {err:.4f}%"
        write_step(s, os.path.join(OUT, fn), f"StrataMetric phantom {p['id']} {p['name']}")
        caps = sorted({r["cap"] for r in plan})
        print(f"{fn:34s} {p['height']:4.0f} {v_true:11.3f} {cav_vol:11.3f} {err:9.6f}% "
              f"{mat/1000:8.1f} cm3  {'yes  ' if hol else 'solid'}  "
              f"{'/'.join(f'{c:g}' for c in caps)} mm")
        truth = dict(cavity_volume_mm3=round(v_true, 3), opening_area_mm2=round(ar, 3),
                     max_depth_mm=round(dep, 3))
        if p.get("cyl"):
            truth.update(opening_area_note="plan view; measured on the cylindrical skin "
                                           "the same opening is skin_area_mm2",
                         skin_area_mm2=round(skin_area(p), 3))
        if p["kind"] == "cylwell":
            # scored with a lid seated - that is what the part is engraved with
            a = assembled(p, LIDS[0])
            truth = dict(cavity_volume_mm3=round(a["volume"], 3),
                         opening_area_mm2=round(a["area"], 3), max_depth_mm=round(a["depth"], 3),
                         truth_note="with lid L1 or L2 seated; with_lid has the rest",
                         chamber_volume_mm3=round(v_true, 3), chamber_area_mm2=round(ar, 3),
                         chamber_depth_mm=round(dep, 3))
        rows[p["id"]] = dict(id=p["id"], file=fn, part="block", height_mm=p["height"],
                             **truth, material_mm3=round(mat, 1),
                             hollow=hol, vents=vent, engraving_depth_mm=ENG,
                             geometry={k: v for k, v in p.items() if k not in ("id", "name")},
                             **({"with_lid": {l["id"]: dict(
                                     {k: round(v, 3) for k, v in assembled(p, l).items()},
                                     extent_by_clock_mm=[round(e, 3) for e in extents(p, l)])
                                   for l in LIDS},
                                 "index_mark": "3 o'clock is the index groove on the top face "
                                               "(+x); 12 o'clock is the edge nearest the top-face "
                                               "'P10' (+y)"}
                                if p["kind"] == "cylwell" else {}),
                             labels=[dict(face=r["face"], text=r["text"], cap_mm=r["cap"],
                                          at=[round(a, 4) for a in r["at"]],
                                          xdir=list(r["xdir"]), normal=list(r["normal"]))
                                     for r in plan],
                             top_labels=[dict(text=p["id"], cap_mm=6.0, centre_xy=[0.0, 33.0],
                                              angle_deg=0.0),
                                         dict(text=f"{KEY_LEN:.3f}", cap_mm=CAP_MIN,
                                              centre_xy=[key_label(p)["x"], key_label(p)["y"]],
                                              angle_deg=key_label(p)["angle"])])
    for l in LIDS:
        if want and l["id"] not in want:
            continue
        plain = volume(lid(l, with_text=False, notch=False))
        s = lid(l, with_text=not no_text)
        exact = math.pi*(l["R_out"]**2 - l["hole_r"]**2)*l["thick"]
        mat = volume(s); total += mat
        fn = f"{l['id']}_{l['name']}.step"
        err = abs(plain - exact)/exact*100
        assert err < 0.01, f"{l['id']} lid volume off by {err:.4f}%"
        write_step(s, os.path.join(OUT, fn), f"StrataMetric lid {l['id']}")
        print(f"{fn:34s} {l['thick']:4.0f} {exact:11.3f} {plain:11.3f} "
              f"{err:9.6f}% {mat/1000:8.1f} cm3  solid  {LID_CAP:g} mm")
        rows[l["id"]] = dict(id=l["id"], file=fn, part="lid", thickness_mm=l["thick"],
                             outer_dia_mm=2*l["R_out"], hole_dia_mm=2*l["hole_r"],
                             hole_offset_mm=l["hole_cx"], material_mm3=round(mat, 1),
                             notch="rim notch at +x, on the side the hole is offset to; "
                                   "line it up with P10's index groove",
                             engraving_depth_mm=ENG,
                             labels=[] if no_text else
                                    [dict(face="underside", text=t, cap_mm=LID_CAP,
                                          arc_radius_mm=LID_RC, centred_at_deg=ang,
                                          letter_tops=side)
                                     for t, ang, side in zip(lid_lines(l), (-90.0, 90.0),
                                                             ("outward", "inward"))])
    print("-"*108)
    print(f"material for the parts built: {total/1000:.0f} cm3")
    order = [p["id"] for p in PHANTOMS] + [l["id"] for l in LIDS]
    merged = {**old, **rows}
    with open(truth_path, "w") as f:
        json.dump([merged[i] for i in order if i in merged], f, indent=2)

if __name__ == "__main__":
    main()
