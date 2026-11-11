"""3D geometry: reference-plane fitting, peri-wound ring, measurements, profiles.

All lengths are millimetres in camera space (x right, y down, z forward) unless a
name says otherwise. The reference plane is oriented so its normal points
towards the camera; `height` is the signed distance from the plane (positive =
raised towards the camera, negative = recessed). Wound depth = max recess.
"""

import numpy as np

from . import imaging

PERI_WOUND_RING_MM = 20.0


# ----------------------------------------------------------------------------- plane

def fit_plane(points, iters=300, inlier_mm=1.5, rng_seed=7):
    """Robust plane fit: RANSAC followed by least-squares refinement on inliers.

    Returns (n, d) with n.x = d for points on the plane, |n| = 1, and n pointing
    towards the camera (n.z < 0).
    """
    pts = np.asarray(points, dtype=np.float64)
    if pts.shape[0] < 3:
        raise ValueError("not enough points to fit a reference plane")
    rng = np.random.default_rng(rng_seed)
    if pts.shape[0] > 20000:
        sample = pts[rng.choice(pts.shape[0], 20000, replace=False)]
    else:
        sample = pts
    best_inl, best = -1, None
    for _ in range(iters):
        a, b, c = sample[rng.choice(sample.shape[0], 3, replace=False)]
        n = np.cross(b - a, c - a)
        nn = np.linalg.norm(n)
        if nn < 1e-9:
            continue
        n = n / nn
        inl = np.count_nonzero(np.abs(sample @ n - n @ a) < inlier_mm)
        if inl > best_inl:
            best_inl, best = inl, (n, n @ a)
    if best is None:
        raise ValueError("degenerate points: could not fit a reference plane")
    n, d = best
    for _ in range(3):  # refine with least squares on inliers (SVD)
        inl = pts[np.abs(pts @ n - d) < max(inlier_mm, 1e-3)]
        if inl.shape[0] < 3:
            break
        c = inl.mean(axis=0)
        _, _, vt = np.linalg.svd(inl - c, full_matrices=False)
        n = vt[-1]
        d = n @ c
    if n[2] > 0:
        n, d = -n, -d
    return n.astype(np.float64), float(d)


def plane_basis(n, length_dir=None):
    """Orthonormal in-plane axes (e1, e2). e1 follows `length_dir` projected on the plane."""
    if length_dir is None:
        length_dir = np.array([1.0, 0.0, 0.0])
    e1 = length_dir - (length_dir @ n) * n
    if np.linalg.norm(e1) < 1e-9:
        e1 = np.array([0.0, 1.0, 0.0]) - n[1] * n
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(n, e1)
    return e1, e2


def ray_plane_points(K, w, h, n, d):
    """Intersection of every pixel's viewing ray with the plane n.x = d -> (h, w, 3) mm."""
    u = np.arange(w, dtype=np.float64)[None, :]
    v = np.arange(h, dtype=np.float64)[:, None]
    rx = (u - K["cx"]) / K["fx"] + 0 * v
    ry = (v - K["cy"]) / K["fy"] + 0 * u
    rz = np.ones_like(rx)
    denom = n[0] * rx + n[1] * ry + n[2] * rz
    with np.errstate(divide="ignore", invalid="ignore"):
        t = d / denom
    return np.stack([rx * t, ry * t, rz * t], axis=-1)


def pixel_areas_on_plane(K, w, h, n, d):
    """Area (mm^2) of each pixel footprint projected onto the reference plane."""
    P = ray_plane_points(K, w, h, n, d)
    Pp = np.pad(P, ((0, 1), (0, 1), (0, 0)), mode="edge")
    dx = Pp[:-1, 1:] - Pp[:-1, :-1]
    dy = Pp[1:, :-1] - Pp[:-1, :-1]
    # edge pixels: reuse the neighbour's differential
    dx[:, -1] = dx[:, -2]
    dy[-1, :] = dy[-2, :]
    return np.linalg.norm(np.cross(dx, dy), axis=-1)


# ----------------------------------------------------------------------------- ring

def peri_wound_ring(points, valid, wound, ring_mm=PERI_WOUND_RING_MM, max_boundary=600):
    """Pixels outside `wound` within `ring_mm` (3D distance) of the wound boundary.

    `points`: (h, w, 3) mm. Pixels with invalid depth are filled before calling.
    """
    h, w = wound.shape
    b = imaging.boundary(wound) & valid
    by, bx = np.nonzero(b)
    if by.size == 0:
        return np.zeros_like(wound)
    if by.size > max_boundary:
        idx = np.linspace(0, by.size - 1, max_boundary).astype(int)
        by, bx = by[idx], bx[idx]
    bp = points[by, bx]                                        # (B, 3)
    # Restrict the search to a padded bounding box around the wound.
    z = float(np.median(bp[:, 2]))
    pad =int(np.ceil(ring_mm / max(1e-3, z) * _focal_from_points(points))) + 4
    ys, xs = np.nonzero(wound)
    y0, y1 = max(0, ys.min() - pad), min(h, ys.max() + pad + 1)
    x0, x1 = max(0, xs.min() - pad), min(w, xs.max() + pad + 1)
    sub = points[y0:y1, x0:x1].reshape(-1, 3)
    best = np.full(sub.shape[0], np.inf, dtype=np.float32)
    for s in range(0, bp.shape[0], 64):
        chunk = bp[s:s + 64]
        d2 = ((sub[:, None, :] - chunk[None, :, :]) ** 2).sum(-1)
        best = np.minimum(best, d2.min(axis=1))
    near = np.zeros((h, w), dtype=bool)
    near[y0:y1, x0:x1] = (best <= ring_mm ** 2).reshape(y1 - y0, x1 - x0)
    return near & ~wound & valid


def _focal_from_points(points):
    """Approximate focal length in pixels from neighbouring camera-space points."""
    h, w, _ = points.shape
    y, x = h // 2, w // 2
    dx = points[y, x + 1, 0] - points[y, x, 0]
    z = points[y, x, 2]
    if dx <= 0 or z <= 0:
        return 1000.0
    return float(z / dx)


# ----------------------------------------------------------------------------- measurements

def feret(points2d):
    """Max Feret diameter of 2D points -> (length, p, q, unit direction)."""
    pts = np.asarray(points2d, dtype=np.float64)
    if pts.shape[0] > 1500:
        pts = pts[np.linspace(0, pts.shape[0] - 1, 1500).astype(int)]
    best, bi, bj = -1.0, 0, 0
    for s in range(0, pts.shape[0], 256):
        d2 = ((pts[s:s + 256, None, :] - pts[None, :, :]) ** 2).sum(-1)
        k = int(np.argmax(d2))
        i, j = divmod(k, pts.shape[0])
        if d2[i, j] > best:
            best, bi, bj = float(d2[i, j]), s + i, j
    p, q = pts[bi], pts[bj]
    L = float(np.sqrt(best))
    direction = (q - p) / L if L > 0 else np.array([1.0, 0.0])
    return L, p, q, direction


def measure(points, valid, wound, ring, K, depth_percentile=99.0):
    """Compute the SOW measurements. Returns (measurements dict, geometry dict)."""
    h, w = wound.shape
    ring_pts = points[ring & valid]
    plane_source = "peri_wound_ring"
    if ring_pts.shape[0] < 50:
        # Ring mostly off-image or invalid: fall back to a wider annulus.
        wide = imaging.dilate(wound, 40) & ~wound & valid
        ring_pts = points[wide]
        plane_source = "wide_annulus"
    n, d = fit_plane(ring_pts)

    height = points @ n - d                       # (h, w) signed distance, + towards camera
    wound_valid = wound & valid
    recess = -height[wound_valid]
    if recess.size == 0:
        raise ValueError("wound region has no valid depth samples")
    depth_mm = float(max(0.0, np.percentile(recess, depth_percentile)))
    max_recess_mm = float(max(0.0, recess.max()))
    mean_recess_mm = float(max(0.0, recess.mean()))
    max_raise_mm = float(max(0.0, (-recess).max()))

    # Wound boundary projected onto the reference plane (ray/plane intersection),
    # so L/W/area describe the opening of the wound on the skin surface.
    P_plane = ray_plane_points(K, w, h, n, d)
    contour = imaging.trace_contour(wound)
    ci = np.clip(np.round(contour).astype(int), 0, [w - 1, h - 1])
    c3 = P_plane[ci[:, 1], ci[:, 0]]
    centroid3 = P_plane[wound].mean(axis=0)

    e1, e2 = plane_basis(n)
    c2 = np.stack([(c3 - centroid3) @ e1, (c3 - centroid3) @ e2], axis=1)
    length, p, q, direc = feret(c2)
    # Rotate the in-plane basis so e1 runs along the length (Feret) axis.
    L_axis3 = direc[0] * e1 + direc[1] * e2
    e1, e2 = plane_basis(n, L_axis3)
    c2 = np.stack([(c3 - centroid3) @ e1, (c3 - centroid3) @ e2], axis=1)
    width = float(c2[:, 1].max() - c2[:, 1].min())

    areas = pixel_areas_on_plane(K, w, h, n, d)
    bed_area_mm2 = float(areas[wound].sum())
    peri_area_mm2 = float(areas[ring].sum())

    # Expected ring area if it were not clipped by the frame/invalid depth
    # (offset-curve area of a convex outline: P*r + pi*r^2).
    perimeter_mm = float(np.linalg.norm(np.diff(np.vstack([c2, c2[:1]]), axis=0), axis=1).sum())
    expected_ring_mm2 = perimeter_mm * PERI_WOUND_RING_MM + np.pi * PERI_WOUND_RING_MM ** 2

    # Length endpoints in the rotated basis.
    lp = np.array([c2[:, 0].min(), 0.0])
    lq = np.array([c2[:, 0].max(), 0.0])

    # Ring outline in plane coordinates for the top-view diagram.
    ring_outer = imaging.trace_contour(fill_ring(ring | wound))
    ri = np.clip(np.round(ring_outer).astype(int), 0, [w - 1, h - 1])
    r3 = P_plane[ri[:, 1], ri[:, 0]] if ri.size else np.zeros((0, 3))
    r2 = np.stack([(r3 - centroid3) @ e1, (r3 - centroid3) @ e2], axis=1) if r3.size else np.zeros((0, 2))

    profile_u, profile_h = cross_section(points, valid, wound | ring, height, centroid3, e1, e2, n, d)

    deepest_idx = np.argmax(np.where(wound_valid, -height, -np.inf))
    dy, dx = divmod(int(deepest_idx), w)
    dp = points[dy, dx]
    deepest_u = float((dp - centroid3) @ e1)

    measurements = {
        "length_mm": round(length, 1),
        "width_mm": round(width, 1),
        "bed_area_cm2": round(bed_area_mm2 / 100.0, 2),
        "depth_mm": round(depth_mm, 1),
        "peri_wound_area_cm2": round(peri_area_mm2 / 100.0, 2),
    }
    geometry = {
        "plane_n": n, "plane_d": np.float64(d),
        "e1": e1, "e2": e2, "centroid": centroid3,
        "outline_uv": c2, "ring_outline_uv": r2,
        "length_uv": np.stack([lp, lq]),
        "width_uv": np.array([[0.0, c2[:, 1].min()], [0.0, c2[:, 1].max()]]),
        "profile_u": profile_u, "profile_h": profile_h,
        "wound_u_range": np.array([c2[:, 0].min(), c2[:, 0].max()]),
        "deepest_u": np.float64(deepest_u), "depth_mm": np.float64(depth_mm),
    }
    quality = {
        "plane_source": plane_source,
        "plane_points": int(ring_pts.shape[0]),
        "plane_rmse_mm": round(float(np.sqrt(np.mean((ring_pts @ n - d) ** 2))), 2),
        "max_recess_mm": round(max_recess_mm, 1),
        "mean_recess_mm": round(mean_recess_mm, 1),
        "max_raise_mm": round(max_raise_mm, 1),
        "perimeter_mm": round(perimeter_mm, 1),
        "ring_coverage": round(min(1.0, peri_area_mm2 / expected_ring_mm2), 2) if expected_ring_mm2 > 0 else None,
        "camera_distance_mm": round(float(np.median(points[wound_valid][:, 2])), 1),
        "wound_valid_fraction": round(float(wound_valid.sum() / max(1, wound.sum())), 3),
        "wound_pixels": int(wound.sum()),
    }
    return measurements, geometry, quality


def fill_ring(m):
    return imaging.fill_holes(m)


def cross_section(points, valid, region, height, centroid3, e1, e2, n, d, band_mm=1.0, step_mm=0.5, margin_mm=25.0):
    """Height profile along the length axis through the wound centroid."""
    sel = region & valid
    P = points[sel] - centroid3
    u = P @ e1
    v = P @ e2
    hh = height[sel]
    on = np.abs(v) <= band_mm
    if on.sum() < 10:
        on = np.abs(v) <= 3 * band_mm
    u, hh = u[on], hh[on]
    if u.size == 0:
        return np.zeros(0), np.zeros(0)
    lo, hi = u.min(), u.max()
    edges = np.arange(lo, hi + step_mm, step_mm)
    idx = np.digitize(u, edges) - 1
    cu, ch = [], []
    for k in range(len(edges) - 1):
        m = idx == k
        if m.any():
            cu.append(edges[k] + step_mm / 2)
            ch.append(float(np.median(hh[m])))
    return np.array(cu), np.array(ch)
