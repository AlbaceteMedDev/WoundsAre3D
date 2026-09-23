"""Minimum wall thickness of each hollow phantom, measured as the smallest
distance from the void's boundary to the part's outer boundary."""
import make_phantoms_step as M
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRep import BRep_Builder
from OCP.TopoDS import TopoDS_Compound

def faces_compound(shape):
    """Faces only - so the distance is boundary to boundary, not zero because
    one solid sits inside the other."""
    c = TopoDS_Compound(); b = BRep_Builder(); b.MakeCompound(c)
    for f in shape.Faces():
        b.Add(c, f.wrapped)
    return c

def min_dist(a, b):
    d = BRepExtrema_DistShapeShape(a, b); d.Perform()
    p2 = d.PointOnShape2(1)
    return d.Value(), (p2.X(), p2.Y(), p2.Z())

print(f"{'ID':5s} {'design wall':>12s} {'with engraving':>15s}   at (x, y, z) mm")
print("-"*72)
for p in M.PHANTOMS:
    blk = M.block(p); cav = M.placed_cavity(p)
    body = M.as_solid(blk.cut(cav)) if cav is not None else M.as_solid(blk)
    body = M.as_solid(body).clean()
    v = M.void_solid(p)
    if v is None or M.volume(v) < 1000 or p["height"] < 12.0:
        print(f"{p['id']:5s} {'solid':>12s}"); continue
    dw, atd = min_dist(v.wrapped, faces_compound(body))
    # same measurement against the engraved (but not hollowed) outer body
    tskin = M.top_skin(blk, M.ENG_TOP); bskin = M.bottom_skin(blk, M.ENG_BOT)
    eng = body
    for t in M.top_tools(p):
        eng = M.safe_cut(eng, t.intersect(tskin))
    idz = M.base_z(p, 0.0)
    eng = M.safe_cut(eng, M.text_prism(p["id"], 6.0, 0.0, 33.0, idz-M.ENG_TOP-2, 10).intersect(tskin))
    lines = M.spec_lines(p); pitch = M.CAP_BOT/0.72*1.09; y0 = (len(lines)-1)*pitch/2
    for k, line in enumerate(lines):
        eng = M.safe_cut(eng, M.text_prism(line, M.CAP_BOT, 0.0, y0-k*pitch, -2.0, 10.0, mirror=True).intersect(bskin))
    de, at = min_dist(v.wrapped, faces_compound(eng))
    ok = "OK" if de >= 0.80 else "FAIL"
    print(f"{p['id']:5s} {dw:10.3f} mm {de:12.3f} mm   design min at ({atd[0]:6.1f},{atd[1]:6.1f},{atd[2]:5.1f})  {ok}")
