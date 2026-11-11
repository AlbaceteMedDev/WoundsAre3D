"""Image, depth-map and binary-mask utilities (numpy + Pillow only, no scipy/OpenCV).

Coordinate conventions
----------------------
* ARKit `capturedImage` is in sensor (landscape) orientation; `sceneDepth.depthMap`
  covers the same field of view at lower resolution (256x192 for 4:3 video
  formats, 256x144 for 16:9). So depth pixel (u, v) maps to RGB pixel
  ((u + 0.5) * W / w - 0.5, (v + 0.5) * H / h - 0.5).
* Intrinsics (fx, fy, cx, cy) refer to the full-resolution RGB image.
* All analysis happens on an "analysis grid": the RGB frame scaled so its long
  side is ANALYSIS_LONG_SIDE pixels, with the depth map resampled onto it.
"""

import io
import math

import numpy as np
from PIL import Image

ANALYSIS_LONG_SIDE = 1024


# ----------------------------------------------------------------------------- frames

def decode_depth(depth_bytes, conf_bytes, rgb_w, rgb_h):
    """Decode raw ARKit float32 depth (metres) + uint8 confidence buffers.

    The grid size is inferred from the byte count and the RGB aspect ratio, so
    both 256x192 (4:3) and 256x144 (16:9) captures work.
    """
    depth = np.frombuffer(depth_bytes, dtype="<f4")
    n = depth.size
    if n == 0:
        raise ValueError("depth.bin is empty")
    w = int(round(math.sqrt(n * rgb_w / rgb_h)))
    candidates = [w, 256, 192]
    for cw in candidates:
        if cw > 0 and n % cw == 0:
            w = cw
            break
    else:
        raise ValueError(f"cannot infer depth grid size from {n} samples")
    h = n // w
    depth = depth.reshape(h, w).astype(np.float32)
    conf = None
    if conf_bytes:
        c = np.frombuffer(conf_bytes, dtype=np.uint8)
        if c.size == n:
            conf = c.reshape(h, w)
    if conf is None:
        conf = np.full((h, w), 2, dtype=np.uint8)
    return depth, conf


def load_rgb(jpeg_bytes):
    img = Image.open(io.BytesIO(jpeg_bytes))
    img.load()
    return img.convert("RGB")


def analysis_size(rgb_w, rgb_h, long_side=ANALYSIS_LONG_SIDE):
    s = long_side / max(rgb_w, rgb_h)
    return int(round(rgb_w * s)), int(round(rgb_h * s))


def sharpness(img, region=0.6):
    """Variance of the Laplacian over the central `region` of a grayscale copy.

    Computed at 960 px long side so scores are comparable between frames.
    """
    g = img.convert("L")
    s = 960 / max(g.size)
    g = g.resize((int(g.size[0] * s), int(g.size[1] * s)), Image.BILINEAR)
    a = np.asarray(g, dtype=np.float32)
    h, w = a.shape
    y0, y1 = int(h * (1 - region) / 2), int(h * (1 + region) / 2)
    x0, x1 = int(w * (1 - region) / 2), int(w * (1 + region) / 2)
    a = a[y0:y1, x0:x1]
    lap = (-4 * a[1:-1, 1:-1] + a[:-2, 1:-1] + a[2:, 1:-1] + a[1:-1, :-2] + a[1:-1, 2:])
    return float(lap.var())


def median3(a, valid):
    """3x3 median filter that ignores invalid samples (returns NaN where none valid)."""
    h, w = a.shape
    p = np.pad(np.where(valid, a, np.nan), 1, mode="edge")
    stack = np.stack([p[dy:dy + h, dx:dx + w] for dy in range(3) for dx in range(3)])
    with np.errstate(all="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            return np.nanmedian(stack, axis=0).astype(np.float32)


def fill_invalid(a, valid, iterations=64):
    """Fill invalid pixels by repeated 4-neighbour averaging (diffusion inpainting)."""
    a = np.where(valid, a, 0).astype(np.float32)
    known = valid.copy()
    for _ in range(iterations):
        if known.all():
            break
        p = np.pad(a, 1, mode="edge")
        k = np.pad(known.astype(np.float32), 1, mode="edge")
        s = (p[:-2, 1:-1] * k[:-2, 1:-1] + p[2:, 1:-1] * k[2:, 1:-1]
             + p[1:-1, :-2] * k[1:-1, :-2] + p[1:-1, 2:] * k[1:-1, 2:])
        c = k[:-2, 1:-1] + k[2:, 1:-1] + k[1:-1, :-2] + k[1:-1, 2:]
        new = (~known) & (c > 0)
        a[new] = s[new] / c[new]
        known = known | new
    return a, known


def resample_bilinear(a, out_w, out_h):
    """Resample a (h, w) float grid covering the same field of view to (out_h, out_w)
    using pixel-centre alignment."""
    h, w = a.shape
    xs = (np.arange(out_w) + 0.5) * w / out_w - 0.5
    ys = (np.arange(out_h) + 0.5) * h / out_h - 0.5
    xs = np.clip(xs, 0, w - 1)
    ys = np.clip(ys, 0, h - 1)
    x0 = np.floor(xs).astype(int)
    y0 = np.floor(ys).astype(int)
    x1 = np.minimum(x0 + 1, w - 1)
    y1 = np.minimum(y0 + 1, h - 1)
    fx = (xs - x0)[None, :]
    fy = (ys - y0)[:, None]
    top = a[y0][:, x0] * (1 - fx) + a[y0][:, x1] * fx
    bot = a[y1][:, x0] * (1 - fx) + a[y1][:, x1] * fx
    return (top * (1 - fy) + bot * fy).astype(np.float32)


def resample_nearest(a, out_w, out_h):
    h, w = a.shape
    xs = np.clip(((np.arange(out_w) + 0.5) * w / out_w).astype(int), 0, w - 1)
    ys = np.clip(((np.arange(out_h) + 0.5) * h / out_h).astype(int), 0, h - 1)
    return a[ys][:, xs]


def scale_intrinsics(K, src_w, src_h, dst_w, dst_h):
    sx, sy = dst_w / src_w, dst_h / src_h
    return {
        "fx": K["fx"] * sx,
        "fy": K["fy"] * sy,
        "cx": (K["cx"] + 0.5) * sx - 0.5,
        "cy": (K["cy"] + 0.5) * sy - 0.5,
        "width": dst_w,
        "height": dst_h,
    }


def backproject(depth_m, K):
    """Return (h, w, 3) camera-space points in millimetres (x right, y down, z forward)."""
    h, w = depth_m.shape
    u = np.arange(w, dtype=np.float32)[None, :]
    v = np.arange(h, dtype=np.float32)[:, None]
    z = depth_m * 1000.0
    x = (u - K["cx"]) / K["fx"] * z
    y = (v - K["cy"]) / K["fy"] * z
    return np.stack([x, y, z], axis=-1).astype(np.float32)


# ----------------------------------------------------------------------------- masks

def _shift_or(m, cross=True):
    p = np.pad(m, 1)
    out = m | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
    if not cross:
        out = out | p[:-2, :-2] | p[:-2, 2:] | p[2:, :-2] | p[2:, 2:]
    return out


def dilate(m, r=1):
    for i in range(r):
        m = _shift_or(m, cross=(i % 2 == 0))
    return m


def erode(m, r=1):
    return ~dilate(~m, r)


def open_close(m, r=2):
    m = dilate(erode(m, r), r)        # open: remove specks
    return erode(dilate(m, r), r)     # close: fill small gaps


def label(m):
    """4-connected component labelling via row runs + union-find.

    Returns an int32 label image (0 = background, 1..N components). Cost scales
    with the number of horizontal runs, not pixels, so it is fast in pure numpy.
    """
    h, w = m.shape
    runs_y, runs_s, runs_e, row_ptr = [], [], [], [0]
    for y in range(h):
        d = np.diff(np.concatenate(([0], m[y].view(np.int8) if m.dtype == bool else (m[y] > 0).astype(np.int8), [0])))
        s = np.flatnonzero(d == 1)
        e = np.flatnonzero(d == -1)
        runs_y.extend([y] * len(s))
        runs_s.extend(s.tolist())
        runs_e.extend(e.tolist())
        row_ptr.append(len(runs_s))
    n = len(runs_s)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for y in range(1, h):
        i, i_end = row_ptr[y - 1], row_ptr[y]
        j, j_end = row_ptr[y], row_ptr[y + 1]
        while i < i_end and j < j_end:
            if runs_s[i] < runs_e[j] and runs_s[j] < runs_e[i]:
                ra, rb = find(i), find(j)
                if ra != rb:
                    parent[max(ra, rb)] = min(ra, rb)
            if runs_e[i] < runs_e[j]:
                i += 1
            else:
                j += 1
    lab = np.zeros((h, w), dtype=np.int32)
    ids = {}
    for k in range(n):
        r = find(k)
        if r not in ids:
            ids[r] = len(ids) + 1
        lab[runs_y[k], runs_s[k]:runs_e[k]] = ids[r]
    return lab


def geodesic_grow(seed, allowed):
    """Connected region of `allowed` reachable from `seed` (4-connectivity)."""
    lab = label(allowed)
    ids = np.unique(lab[seed & allowed])
    ids = ids[ids > 0]
    return np.isin(lab, ids) if ids.size else np.zeros_like(allowed)


def fill_holes(m):
    lab = label(~m)
    edge = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    holes = (lab > 0) & ~np.isin(lab, edge)
    return m | holes


def component_at(m, x, y, search_px=40):
    """The connected component of `m` containing (x, y), or the one nearest to it."""
    h, w = m.shape
    lab = label(m)
    xi, yi = int(round(x)), int(round(y))
    if 0 <= yi < h and 0 <= xi < w and lab[yi, xi]:
        return lab == lab[yi, xi]
    ys, xs = np.nonzero(lab)
    if ys.size == 0:
        return np.zeros_like(m)
    d2 = (xs - x) ** 2 + (ys - y) ** 2
    i = int(np.argmin(d2))
    if d2[i] > search_px ** 2:
        return np.zeros_like(m)
    return lab == lab[ys[i], xs[i]]


def boundary(m):
    """Mask pixels with at least one 4-neighbour outside the mask."""
    return m & ~erode(m, 1)


def trace_contour(m):
    """Moore-neighbour trace of the outer boundary of the largest blob in `m`.

    Returns an (N, 2) float array of (x, y) pixel coordinates, clockwise in image
    space, or an empty array if `m` is empty.
    """
    ys, xs = np.nonzero(m)
    if ys.size == 0:
        return np.zeros((0, 2))
    p = np.pad(m, 1)
    i = int(np.lexsort((xs, ys))[0])
    start = (ys[i] + 1, xs[i] + 1)                 # top-most, then left-most (padded coords)
    # 8 neighbours clockwise starting West
    nb = [(0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1)]
    contour = [start]
    cur = start
    back = 0                                      # we entered `start` from the west
    max_len = 4 * int(m.sum()) + 8
    for _ in range(max_len):
        found = False
        for k in range(8):
            d = (back + 1 + k) % 8
            ny, nx = cur[0] + nb[d][0], cur[1] + nb[d][1]
            if p[ny, nx]:
                back = (d + 4) % 8                # direction pointing back to `cur`
                cur = (ny, nx)
                found = True
                break
        if not found:                             # isolated pixel
            break
        if cur == start and len(contour) > 1:
            break
        contour.append(cur)
    c = np.array(contour, dtype=float)
    return np.stack([c[:, 1] - 1, c[:, 0] - 1], axis=1)


def mask_to_png(m):
    buf = io.BytesIO()
    Image.fromarray((m.astype(np.uint8) * 255)).save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def png_to_mask(data, size=None):
    img = Image.open(io.BytesIO(data)).convert("L")
    if size and img.size != tuple(size):
        img = img.resize(tuple(size), Image.NEAREST)
    return np.asarray(img) > 127
