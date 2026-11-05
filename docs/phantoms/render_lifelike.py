"""Colour pictures of the lifelike wound phantoms, from their 3MF files.

Each part is drawn from the same angle and at the same scale as the P-series
pictures (render_parts.py): cavity up, key line nearest. A second, closer view
looks straight down on the wound, which is how a wound is photographed and
the view to compare tissue colours in. Writes renders/lifelike/<id>.png and
<id>_top.png.

    python render_lifelike.py          # all parts
    python render_lifelike.py W4       # just these
"""
import math
import os
import re
import sys
import zipfile
import numpy as np
from PIL import Image
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
import render_parts as RP

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "lifelike")
OUT = os.path.join(HERE, "renders", "lifelike")

def read_3mf(path):
    """Vertices, triangles and per-corner sRGB colours of a single-object 3MF."""
    with zipfile.ZipFile(path) as z:
        xml = z.read("3D/3dmodel.model").decode()
    cols = np.array([int(h, 16) for h in re.findall(r'<m:color color="#([0-9A-Fa-f]{6})"', xml)])
    v = np.array(re.findall(r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', xml), float)
    t = np.array(re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)" pid="\d+" '
                            r'p1="(\d+)" p2="(\d+)" p3="(\d+)"', xml), np.int64)
    c = cols[t[:, 3:]]
    rgb = np.stack([(c >> 16) & 255, (c >> 8) & 255, c & 255], -1).astype(np.uint8)
    return v, t[:, :3], rgb

def polydata(v, t, rgb):
    pts = v[t].reshape(-1, 3)
    pd = vtk.vtkPolyData()
    vp = vtk.vtkPoints(); vp.SetData(numpy_to_vtk(pts.astype(np.float64), deep=True)); pd.SetPoints(vp)
    n = len(t)
    offsets = numpy_to_vtkIdTypeArray(np.arange(0, 3*n + 1, 3, dtype=np.int64), deep=True)
    conn = numpy_to_vtkIdTypeArray(np.arange(3*n, dtype=np.int64), deep=True)
    ca = vtk.vtkCellArray(); ca.SetData(offsets, conn); pd.SetPolys(ca)
    col = numpy_to_vtk(rgb.reshape(-1, 3), deep=True); col.SetName("Colors")
    pd.GetPointData().SetScalars(col)
    nf = vtk.vtkPolyDataNormals(); nf.SetInputData(pd); nf.ComputePointNormalsOff()
    nf.ComputeCellNormalsOn(); nf.SplittingOff(); nf.Update()
    return nf.GetOutput()

def render(pd, centre, out, elev, azim, scale, size):
    m = vtk.vtkPolyDataMapper(); m.SetInputData(pd); m.SetScalarModeToUsePointData()
    m.SetColorModeToDirectScalars()
    a = vtk.vtkActor(); a.SetMapper(m)
    pr = a.GetProperty(); pr.SetAmbient(0.22); pr.SetDiffuse(0.80); pr.SetSpecular(0.05)
    r = vtk.vtkRenderer(); r.AddActor(a); r.SetBackground(1, 1, 1); r.AutomaticLightCreationOff()
    for direction, power in (((-0.3, -0.45, 1.0), 0.95), ((0.8, -0.5, 0.3), 0.30)):
        li = vtk.vtkLight(); li.SetLightTypeToSceneLight(); li.SetPositional(False)
        li.SetFocalPoint(0, 0, 0); li.SetPosition(*direction); li.SetIntensity(power); r.AddLight(li)
    ao = vtk.vtkSSAOPass(); ao.SetRadius(1.2); ao.SetBias(0.15); ao.SetKernelSize(96)
    ao.BlurOn(); ao.SetDelegatePass(vtk.vtkRenderStepsPass()); r.SetPass(ao)
    W, H = size
    w = vtk.vtkRenderWindow(); w.SetOffScreenRendering(1); w.AddRenderer(r); w.SetSize(W*2, H*2)
    cam = r.GetActiveCamera(); cam.ParallelProjectionOn()
    az, el = math.radians(azim), math.radians(elev)
    d = np.array([math.sin(az)*math.cos(el), -math.cos(az)*math.cos(el), math.sin(el)])
    cam.SetFocalPoint(*centre); cam.SetPosition(*(np.array(centre) + 400*d))
    cam.SetViewUp(0, 1, 0) if elev > 89 else cam.SetViewUp(0, 0, 1)
    cam.SetParallelScale(scale); r.ResetCameraClippingRange(); w.Render()
    g = vtk.vtkWindowToImageFilter(); g.SetInput(w); g.ReadFrontBufferOff(); g.Update()
    img = g.GetOutput(); x, y, _ = img.GetDimensions()
    arr = np.frombuffer(memoryview(img.GetPointData().GetScalars()), np.uint8).reshape(y, x, -1)[::-1, :, :3]
    Image.fromarray(arr).resize((W, H), Image.LANCZOS).save(out, optimize=True)

def main(ids):
    os.makedirs(OUT, exist_ok=True)
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(".3mf"):
            continue
        pid = f.split("_")[0]
        if ids and pid not in ids:
            continue
        v, t, rgb = read_3mf(os.path.join(SRC, f))
        pd = polydata(v, t, rgb)
        lo, hi = v.min(0), v.max(0)
        centre = tuple((lo + hi)/2)
        render(pd, centre, os.path.join(OUT, f"{pid}.png"), RP.ELEV, RP.AZIM, RP.SCALE, (RP.W, RP.H))
        top = (0.0, 1.5, hi[2])
        # the wound and its periwound only: the part number and key line sit outside
        render(pd, top, os.path.join(OUT, f"{pid}_top.png"), 90.0, 0.0, 27.5, (1000, 1000))
        print(pid, len(t), "triangles")

if __name__ == "__main__":
    main(set(sys.argv[1:]))
