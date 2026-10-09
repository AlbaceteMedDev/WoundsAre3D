"""Minimum wall thickness of each hollow phantom, measured as the smallest
distance from the void's boundary to the part's outer boundary - first on the
plain block, then on the finished outer surface with every engraving cut (top,
side walls and underside). Vents are left out: they pass through the wall on
purpose."""
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

print(f"{'ID':5s} {'design wall':>12s} {'with engraving':>15s}   thinnest at (x, y, z) mm")
print("-"*80)
all_ok = True
for p in M.PHANTOMS:
    blk = M.block(p); cav = M.placed_cavity(p)
    body = M.as_solid(blk.cut(cav)) if cav is not None else M.as_solid(blk)
    body = M.as_solid(body).clean()
    v = M.void_solid(p)
    if v is None or M.volume(v) < 1000 or p["height"] < 12.0:
        print(f"{p['id']:5s} {'solid':>12s}"); continue
    dw, _ = min_dist(v.wrapped, faces_compound(body))
    eng = M.build(p, with_text=True, hollow=False)[0]
    de, at = min_dist(v.wrapped, faces_compound(eng))
    ok = de >= 0.80
    all_ok &= ok
    print(f"{p['id']:5s} {dw:10.3f} mm {de:12.3f} mm   ({at[0]:6.1f},{at[1]:6.1f},{at[2]:5.1f})"
          f"  {'OK' if ok else 'FAIL'}")
print("-"*80)
print("ALL OK" if all_ok else "SOME FAILED")
