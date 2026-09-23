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
ENG_TOP, ENG_BOT = 0.5, 0.4 # engraving depths
KEY_LEN, KEY_Y, KEY_W = 50.0, -30.0, 0.8
TICK_W, TICK_H = 0.8, 6.0
DOT_R, DOT_XY = 1.25, 32.0
CAP_BOT = 4.0               # bottom spec plate cap height - prints at 0.6 mm min detail
MIN_VOID = 4.0              # below this the block stays solid; hollowing buys nothing
VENT_MAX = 8.0              # powder escape holes through the side walls

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

def stadium(R, seg, h, n=48, tmin=0.02):
    """Trough of depth h(1-(d/R)^2), d the distance to the segment |x|<=seg/2.
    Lofted through stadium sections of half-width R*t at z = -h(1-t^2), the
    same parameterisation that makes the paraboloids come out exact."""
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

def top_skin(solid, depth):
    """The top `depth` of the solid, following whatever shape the top has."""
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
    return tools + [groove] + ticks

def text_prism(txt, cap, x, y, z0, height, mirror=False, halign="center"):
    w = (cq.Workplane("XY").workplane(offset=z0)
           .text(txt, cap/0.72, height, font="DejaVu Sans Mono", kind="bold",
                 halign=halign, valign="center", clean=True))
    s = w.val().translate((x, y, 0))
    if mirror:
        s = s.mirror("YZ")
        s = s.translate((2*x, 0, 0)) if abs(x) > 1e-9 else s
    return s

def spec_lines(p):
    vol, ar, dep = analytic(p)
    k = p["kind"]
    geom = {"hemisphere": [f"SPHERE R {p.get('R',0):.3f}"],
            "cone":       [f"CONE R {p.get('R',0):.3f}"],
            "paraboloid": [f"a{p.get('a',0):.3f} b{p.get('b',0):.3f}"],
            "lobed":      [f"R0 {p.get('R0',0):.3f} mm", "LOBES 3:.18 5:.10"],
            "stadium":    [f"L{p.get('seg',0):.3f} R{p.get('R',0):.3f}"],
            "cylwell":    [f"CHAMBER R {p.get('R',0):.3f}"]}.get(k, ["NO CAVITY"])
    shape = {"hemisphere": "HEMISPHERE", "cone": "CONE", "paraboloid": "ELL. PARABOLOID",
             "lobed": "LOBED PARABOLOID", "stadium": "STADIUM TROUGH",
             "cylwell": "CYL. WELL + LID", "flat": "FLAT PLATE"}[k]
    lines = [f"STRATAMETRIC {p['id']}", shape] + geom
    lines += [f"DEPTH  {dep:8.3f} mm", f"AREA   {ar:8.2f} mm2",
              f"VOL  {vol:10.2f} mm3", f"VOL  {vol/1000:10.3f} cm3"]
    if p.get("cyl"):   lines.append(f"CYL BASE R {p['cyl']:.1f} mm")
    if k == "cylwell": lines.append("USE WITH LID L1/L2")
    lines += ["KEY LINE  50.000 mm", f"BLOCK 80x80x{p['height']:.0f} mm", "CAD EXACT-VERIFY"]
    return lines

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
        sol = (cq.Workplane("XY").workplane(offset=H - h - w)
                 .slot2D(seg + 2*(R + g), 2*(R + g), 0).extrude(h + w + 1).val())
        return sol
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

def safe_cut(a, b, fuzzy=(0.0, 1e-5, 1e-4, 1e-3)):
    """Boolean cut that retries with a fuzzy tolerance; OCC returns a null shape
    rather than raising when two surfaces meet within its default tolerance."""
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
                return as_solid(r)
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
        v = safe_cut(v, gc)
    sl = v.Solids()
    return max(sl, key=lambda s: s.Volume()).clean() if sl else None

def vents(p, zlo, zhi, dia, void=None):
    """Powder escape holes through the +X and -X walls, run outboard at y = +-33
    so they stay clear of every cavity footprint and of the top-face engravings."""
    zc = 0.5*(zlo + zhi)
    out = []
    for sy in (-1, 1):
        hole = (cq.Workplane("YZ").workplane(offset=-L)
                  .center(sy*33.0, zc).circle(dia/2).extrude(2*L).val())
        if void is not None and volume(hole.intersect(void)) < 0.25*math.pi*(dia/2)**2:
            continue                     # would not actually reach the void
        out.append(hole)
    return out

# -------------------------------------------------------------------- lids ---
def lid(l):
    d = (cq.Workplane("XY").circle(l["R_out"]).extrude(l["thick"])
           .faces(">Z").workplane().center(l["hole_cx"], 0).circle(l["hole_r"])
           .cutThruAll())
    return d.val()

# -------------------------------------------------------------------- step ---
def write_step(shape, path, name):
    Interface_Static.SetCVal_s("write.step.product.name", name)
    Interface_Static.SetIVal_s("write.step.schema", 3)          # AP214
    w = STEPControl_Writer()
    w.Transfer(shape.wrapped, STEPControl_AsIs)
    if w.Write(path) != IFSelect_RetDone:
        raise RuntimeError(f"STEP write failed for {path}")

# -------------------------------------------------------------------- main ---
def build(p, with_text=True):
    blk = block(p)
    solid_block_vol = volume(blk)
    cav = placed_cavity(p)
    body = as_solid(blk.cut(cav)) if cav is not None else as_solid(blk)
    cav_vol = solid_block_vol - volume(body)
    if p["kind"] == "cylwell":
        cav_vol -= math.pi*p["pocket_r"]**2*p["pocket_d"]

    # Skins are taken from the un-engraved solid: the engravings are 0.4-0.5 mm
    # and must not take part in the offset, or the wall would be measured from
    # the bottom of a groove.
    tskin = top_skin(blk, ENG_TOP)
    bskin = bottom_skin(blk, ENG_BOT)

    body = as_solid(body).clean()
    v = void_solid(p)
    ve = None
    if v is not None and volume(v) > 1000.0:
        bb = v.BoundingBox(); ve = (bb.zmin, bb.zmax)
    hollowed = bool(ve and (ve[1] - ve[0]) >= MIN_VOID and p["height"] >= 12.0)
    h = as_solid(body.cut(v)) if hollowed else body
    if hollowed:
        dia = min(VENT_MAX, (ve[1] - ve[0]) - 1.0)
        for vt in vents(p, ve[0], ve[1], dia, void=v):
            h = safe_cut(h, vt)
        body = h

    for t in top_tools(p):
        body = safe_cut(body, t.intersect(tskin))
    idz = base_z(p, 0.0)
    body = safe_cut(body, text_prism(p["id"], 6.0, 0.0, 33.0, idz - ENG_TOP - 2, 10)
                          .intersect(tskin))
    body = safe_cut(body, text_prism("50.000", 3.2, 0.0, -36.0, idz - ENG_TOP - 2, 10)
                          .intersect(tskin))

    if with_text:
        lines = spec_lines(p)
        pitch = CAP_BOT/0.72*1.09
        y0 = (len(lines) - 1)*pitch/2.0
        for k, line in enumerate(lines):
            tp = text_prism(line, CAP_BOT, 0.0, y0 - k*pitch, -2.0, 10.0, mirror=True)
            body = safe_cut(body, tp.intersect(bskin))
    return body, cav_vol, solid_block_vol, hollowed

def main():
    os.makedirs(OUT, exist_ok=True)
    want = set(a for a in sys.argv[1:] if not a.startswith("-"))
    no_text = "--no-text" in sys.argv
    rows, total = [], 0.0
    print(f"{'file':34s} {'H':>4s} {'V_true':>11s} {'B-rep':>11s} {'err':>10s} "
          f"{'material':>10s}  hollow")
    print("-"*96)
    for p in PHANTOMS:
        if want and p["id"] not in want:
            continue
        s, cav_vol, blk_vol, hol = build(p, with_text=not no_text)
        v_true, ar, dep = analytic(p)
        err = 0.0 if v_true == 0 else abs(cav_vol - v_true)/v_true*100
        mat = volume(s)
        total += mat
        fn = f"{p['id']}_{p['name']}.step"
        write_step(s, os.path.join(OUT, fn), f"StrataMetric phantom {p['id']} {p['name']}")
        print(f"{fn:34s} {p['height']:4.0f} {v_true:11.3f} {cav_vol:11.3f} {err:9.6f}% "
              f"{mat/1000:8.1f} cm3  {'yes' if hol else 'solid'}")
        assert err < 0.01, f"{p['id']} cavity volume off by {err:.4f}%"
        rows.append(dict(id=p["id"], file=fn, part="block", height_mm=p["height"],
                         cavity_volume_mm3=round(v_true, 3), opening_area_mm2=round(ar, 3),
                         max_depth_mm=round(dep, 3), material_mm3=round(mat, 1),
                         hollow=hol))
    for l in LIDS:
        if want and l["id"] not in want:
            continue
        s = lid(l)
        exact = math.pi*(l["R_out"]**2 - l["hole_r"]**2)*l["thick"]
        mat = volume(s); total += mat
        fn = f"{l['id']}_{l['name']}.step"
        write_step(s, os.path.join(OUT, fn), f"StrataMetric lid {l['id']}")
        print(f"{fn:34s} {l['thick']:4.0f} {exact:11.3f} {mat:11.3f} "
              f"{abs(mat-exact)/exact*100:9.6f}% {mat/1000:8.1f} cm3  solid")
        rows.append(dict(id=l["id"], file=fn, part="lid", thickness_mm=l["thick"],
                         outer_dia_mm=2*l["R_out"], hole_dia_mm=2*l["hole_r"],
                         hole_offset_mm=l["hole_cx"], material_mm3=round(mat, 1)))
    print("-"*96)
    print(f"material for the set: {total/1000:.0f} cm3")
    with open(os.path.join(HERE, "truth_step.json"), "w") as f:
        json.dump(rows, f, indent=2)

if __name__ == "__main__":
    main()
