"""Pictures of the twelve parts, for matching a printed part to its sizes.

Renders each STEP file in step/ - the geometry that is sent to print, engraving
and all - to renders/<id>.png, every part from the same angle and at the same
scale, so the pictures compare as the parts do on the bench: cavity up, the key
line along the near edge, the side wall with the part number facing front-left.
The lids are seen from higher up, so the offset of L2's hole shows.

Needs cadquery (OpenCASCADE and VTK) and, on a machine without a display, the
OSMesa library for off-screen rendering (Debian/Ubuntu: apt install libosmesa6).

    python render_parts.py            # all parts
    python render_parts.py P9 L2      # just these
"""
import math
import os
import sys
import numpy as np
from PIL import Image
import cadquery as cq
from OCP.BRep import BRep_Tool
from OCP.BRepLib import BRepLib_ToolTriangulatedShape
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
import make_phantoms_step as M

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "renders")
W, H, SS = 1200, 860, 2           # output pixels, supersampling for antialiasing
DEFLECT, ANGLE = 0.02, 0.12        # mesh tolerance: mm, radians
AZIM, ELEV = 32.0, 38.0            # view: degrees round from the front, and up
LID_ELEV = 62.0                    # the lids from higher up, to show where the hole sits
SCALE = 50.0                       # half the view height, mm; the same for every part
GREY = (0.80, 0.80, 0.78)          # natural PA12

def files():
    for p in M.PHANTOMS + M.LIDS:
        yield p["id"], os.path.join(HERE, "step", f"{p['id']}_{p['name']}.step")

def mesh(shape):
    """Triangles of every face, with the surface's own normals at the nodes, so
    curved faces shade smoothly and edges stay sharp."""
    BRepMesh_IncrementalMesh(shape, DEFLECT, False, ANGLE, True)
    pts, nrm, tris, base = [], [], [], 0
    ex = TopExp_Explorer(shape, TopAbs_FACE)
    while ex.More():
        f = TopoDS.Face_s(ex.Current()); ex.Next()
        loc = TopLoc_Location()
        t = BRep_Tool.Triangulation_s(f, loc)
        if t is None:
            continue
        BRepLib_ToolTriangulatedShape.ComputeNormals_s(f, t)
        tr = loc.Transformation()
        rev = f.Orientation() == TopAbs_REVERSED
        n = t.NbNodes()
        for i in range(1, n + 1):
            p = t.Node(i).Transformed(tr)
            pts.append((p.X(), p.Y(), p.Z()))
            v = t.Normal(i).Transformed(tr)
            s = -1.0 if rev else 1.0
            nrm.append((s*v.X(), s*v.Y(), s*v.Z()))
        for i in range(1, t.NbTriangles() + 1):
            a, b, c = t.Triangle(i).Get()
            tris.append((base + a - 1, base + c - 1, base + b - 1) if rev else
                        (base + a - 1, base + b - 1, base + c - 1))
        base += n
    return np.array(pts), np.array(nrm), np.array(tris, dtype=np.int64)

def polydata(pts, nrm, tris):
    pd = vtk.vtkPolyData()
    vp = vtk.vtkPoints(); vp.SetData(numpy_to_vtk(pts.astype(np.float64), deep=True))
    pd.SetPoints(vp)
    offsets = numpy_to_vtkIdTypeArray(np.arange(0, 3*len(tris) + 1, 3, dtype=np.int64), deep=True)
    conn = numpy_to_vtkIdTypeArray(tris.ravel().astype(np.int64), deep=True)
    ca = vtk.vtkCellArray(); ca.SetData(offsets, conn)
    pd.SetPolys(ca)
    n = numpy_to_vtk(nrm.astype(np.float32), deep=True); n.SetName("Normals")
    pd.GetPointData().SetNormals(n)
    return pd

def render(pd, centre, out, elev=ELEV):
    m = vtk.vtkPolyDataMapper(); m.SetInputData(pd)
    a = vtk.vtkActor(); a.SetMapper(m)
    pr = a.GetProperty()
    pr.SetColor(*GREY); pr.SetAmbient(0.20); pr.SetDiffuse(0.82)
    pr.SetSpecular(0.06); pr.SetSpecularPower(20); pr.SetInterpolationToPhong()
    r = vtk.vtkRenderer(); r.AddActor(a); r.SetBackground(1, 1, 1)
    r.AutomaticLightCreationOff()
    # key light from above, front-left: the top reads lightest, the front wall
    # mid-grey and the right wall darkest, as a part on a bench under a lamp
    for direction, power in (((-0.3, -0.45, 1.0), 1.0), ((0.8, -0.5, 0.3), 0.35)):
        li = vtk.vtkLight(); li.SetLightTypeToSceneLight(); li.SetPositional(False)
        li.SetFocalPoint(0, 0, 0); li.SetPosition(*direction); li.SetIntensity(power)
        r.AddLight(li)
    # ambient occlusion darkens the engraved grooves, so the lettering reads
    ao = vtk.vtkSSAOPass(); ao.SetRadius(1.5); ao.SetBias(0.15); ao.SetKernelSize(128)
    ao.BlurOn(); ao.SetDelegatePass(vtk.vtkRenderStepsPass()); r.SetPass(ao)
    w = vtk.vtkRenderWindow(); w.SetOffScreenRendering(1); w.AddRenderer(r)
    w.SetSize(W*SS, H*SS)
    cam = r.GetActiveCamera(); cam.ParallelProjectionOn()
    az, el = math.radians(AZIM), math.radians(elev)
    d = np.array([math.sin(az)*math.cos(el), -math.cos(az)*math.cos(el), math.sin(el)])
    cam.SetFocalPoint(*centre); cam.SetPosition(*(np.array(centre) + 400*d))
    cam.SetViewUp(0, 0, 1); cam.SetParallelScale(SCALE)
    r.ResetCameraClippingRange()
    w.Render()
    g = vtk.vtkWindowToImageFilter(); g.SetInput(w); g.ReadFrontBufferOff(); g.Update()
    img = g.GetOutput()
    x, y, _ = img.GetDimensions()
    arr = np.frombuffer(memoryview(img.GetPointData().GetScalars()), np.uint8)
    arr = arr.reshape(y, x, -1)[::-1, :, :3]
    Image.fromarray(arr).convert("L").resize((W, H), Image.LANCZOS).save(out, optimize=True)

def main(ids):
    os.makedirs(OUT, exist_ok=True)
    for pid, path in files():
        if ids and pid not in ids:
            continue
        shape = cq.importers.importStep(path).val().wrapped
        pts, nrm, tris = mesh(shape)
        lo, hi = pts.min(0), pts.max(0)
        centre = tuple((lo + hi)/2)        # each part centred; the scale is shared
        out = os.path.join(OUT, f"{pid}.png")
        render(polydata(pts, nrm, tris), centre, out, LID_ELEV if pid.startswith("L") else ELEV)
        print(f"{pid}: {len(tris):,} triangles, {hi[2] - lo[2]:.1f} mm tall -> {out}")

if __name__ == "__main__":
    main(set(sys.argv[1:]))
