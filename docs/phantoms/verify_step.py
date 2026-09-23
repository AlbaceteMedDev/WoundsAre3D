"""Re-import every STEP file cold, the way a print service's software will, and
check it comes back as one valid closed solid of the expected volume."""
import glob, os, json
from OCP.STEPControl import STEPControl_Reader
from OCP.IFSelect import IFSelect_RetDone
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.ShapeAnalysis import ShapeAnalysis_FreeBounds
from OCP.TopAbs import TopAbs_SOLID, TopAbs_FACE
from OCP.TopExp import TopExp_Explorer

here = os.path.dirname(os.path.abspath(__file__))
built = {r["file"]: r for r in json.load(open(os.path.join(here, "truth_step.json")))}
print(f"{'file':34s} {'KB':>6s} {'solids':>6s} {'faces':>6s} {'valid':>6s} {'closed':>7s} {'vol cm3':>9s} {'vs build':>9s}")
print("-"*92)
ok_all = True
for fn in sorted(glob.glob(os.path.join(here, "step", "*.step")), key=lambda s: (len(os.path.basename(s)), s)):
    r = STEPControl_Reader()
    if r.ReadFile(fn) != IFSelect_RetDone:
        print(os.path.basename(fn), "READ FAILED"); ok_all = False; continue
    r.TransferRoots(); sh = r.OneShape()
    ns = 0; ex = TopExp_Explorer(sh, TopAbs_SOLID)
    while ex.More(): ns += 1; ex.Next()
    nf = 0; ex = TopExp_Explorer(sh, TopAbs_FACE)
    while ex.More(): nf += 1; ex.Next()
    valid = BRepCheck_Analyzer(sh).IsValid()
    fb = ShapeAnalysis_FreeBounds(sh)
    closed = fb.GetClosedWires().IsNull() and fb.GetOpenWires().IsNull()   # no free edges
    g = GProp_GProps(); BRepGProp.VolumeProperties_s(sh, g, 1e-8, True); v = g.Mass()
    want = built.get(os.path.basename(fn), {}).get("material_mm3")
    dv = "" if want is None else f"{(v-want)/want*100:+.4f}%"
    good = ns == 1 and valid and closed and (want is None or abs(v-want)/want < 1e-4)
    ok_all &= good
    print(f"{os.path.basename(fn):34s} {os.path.getsize(fn)/1024:6.0f} {ns:6d} {nf:6d} {str(valid):>6s} "
          f"{str(closed):>7s} {v/1000:9.2f} {dv:>9s}  {'OK' if good else 'FAIL'}")
print("-"*92)
print("ALL OK" if ok_all else "SOME FAILED")
