"""Undermining: lateral wound extension beneath intact periwound skin.

A clinician probes under the wound edge at clock positions and records how far
the probe advances (the *extent*, in mm). Two quantities follow from those
readings together with the wound boundary:

* the **undermined area** -- the projected area of intact skin that has been
  separated from the wound bed. This is the clinical number: how much skin is
  detached, and the figure that drives dressing and graft sizing.
* the **undermined volume** -- that area multiplied by the height of the
  pocket. The probe does not measure pocket height, so the height used here is
  an assumption supplied by the caller and is reported back as such.

Geometry. The undermined region is the set of points lying outside the wound
boundary but within ``u(s)`` of it, where ``s`` is arc length around the
boundary and ``u`` is the probe extent interpolated around it. The region is
evaluated on a raster, which is robust to concave boundaries; offsetting the
boundary polygon directly would self-intersect wherever the extent exceeds the
local radius of curvature. For a circular wound of edge radius ``R`` with
uniform extent ``u`` the result reduces to the annulus ``pi((R+u)^2 - R^2)``,
available in closed form as :func:`annulus_undermining`.

Note on extent interpolation: extents are splined in **arc length**, not in
azimuth. On an irregular wound equal angles are not equal distances along the
edge, and splining in azimuth over-weights the lobes.

Undermining cannot be observed optically -- no camera or depth sensor sees
under intact skin -- so these inputs are always clinician-entered and every
output here must be labelled as probe-derived rather than instrument-derived.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy.interpolate import CubicSpline

_EPS = 1e-12
_PROFILE_SAMPLES = 720
_INVOLVED_THRESHOLD_MM = 0.5


@dataclass(frozen=True)
class UnderminingMeasurement:
    """A single radial undermining measurement.

    Attributes
    ----------
    clock_position_hours : float
        Clinical clock notation (0..12]. 12 is at the head/north of the wound
        and the sequence runs clockwise.
    radial_extent_mm : float
        How far the probe advances under intact skin from the wound edge.
    """

    clock_position_hours: float
    radial_extent_mm: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.clock_position_hours <= 12.0):
            raise ValueError(
                f"clock_position_hours must be in [0, 12], got {self.clock_position_hours}"
            )
        if self.radial_extent_mm < 0:
            raise ValueError("radial_extent_mm must be nonnegative")


@dataclass(frozen=True)
class UnderminingResult:
    """Undermining measured from a wound boundary and a set of probe readings."""

    undermined_area_mm2: float
    visible_area_mm2: float
    total_area_mm2: float
    undermined_volume_mm3: float
    undermined_area_ci95_mm2: tuple[float, float]
    undermined_volume_ci95_mm3: tuple[float, float]
    max_extent_mm: float
    max_extent_clock_hours: float
    involved_clock_positions: tuple[float, ...]
    pocket_height_mm: float
    pocket_height_basis: str
    n_measurements: int
    grid_pitch_mm: float


def _clock_to_theta(clock_hours: float) -> float:
    """Clinical clock notation to a standard angle in radians.

    12 o'clock -> +y axis -> theta = pi/2; 3 o'clock -> +x axis -> theta = 0;
    the clinical sequence runs clockwise, i.e. toward negative theta.
    """
    return np.pi / 2.0 - (clock_hours / 12.0) * 2.0 * np.pi


def _theta_to_clock(theta: float) -> float:
    """Inverse of :func:`_clock_to_theta`, returned on (0, 12]."""
    hours = ((np.pi / 2.0 - theta) / (2.0 * np.pi)) * 12.0
    hours = float(np.mod(hours, 12.0))
    return 12.0 if hours == 0.0 else hours


def _as_open_polygon(boundary_mm: Sequence[Sequence[float]]) -> np.ndarray:
    pts = np.asarray(boundary_mm, dtype=np.float64)
    if pts.ndim != 2 or pts.shape[1] != 2:
        raise ValueError(f"boundary must be (N, 2), got shape {pts.shape}")
    if len(pts) >= 2 and np.allclose(pts[0], pts[-1]):
        pts = pts[:-1]
    if len(pts) < 3:
        raise ValueError("boundary needs at least 3 distinct vertices")
    return pts


def polygon_centroid(poly: np.ndarray) -> tuple[float, float]:
    """Area-weighted centroid of a simple polygon (falls back to the vertex mean)."""
    x, y = poly[:, 0], poly[:, 1]
    xn, yn = np.roll(x, -1), np.roll(y, -1)
    cross = x * yn - xn * y
    area2 = cross.sum()
    if abs(area2) < _EPS:
        return float(x.mean()), float(y.mean())
    cx = float(((x + xn) * cross).sum() / (3.0 * area2))
    cy = float(((y + yn) * cross).sum() / (3.0 * area2))
    return cx, cy


def polygon_area(poly: np.ndarray) -> float:
    """Unsigned area of a simple polygon by the shoelace formula (mm^2)."""
    x, y = poly[:, 0], poly[:, 1]
    return float(abs(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)) / 2.0)


def _segments(poly: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
    """Segment starts, directions, lengths, cumulative arc length, perimeter."""
    A = poly
    B = np.roll(poly, -1, axis=0)
    D = B - A
    seg_len = np.hypot(D[:, 0], D[:, 1])
    s_start = np.concatenate([[0.0], np.cumsum(seg_len)[:-1]])
    return A, D, seg_len, s_start, float(seg_len.sum())


def _distance_and_arclength(poly: np.ndarray, pts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """For each point, distance to the polygon boundary and the arc length of the
    nearest boundary point."""
    A, D, seg_len, s_start, _ = _segments(poly)
    best_d = np.full(len(pts), np.inf)
    best_s = np.zeros(len(pts))
    for i in range(len(A)):
        d = D[i]
        ll = float(d[0] * d[0] + d[1] * d[1])
        w = pts - A[i]
        t = np.zeros(len(pts)) if ll < _EPS else np.clip((w @ d) / ll, 0.0, 1.0)
        proj = A[i] + t[:, None] * d
        dist = np.hypot(pts[:, 0] - proj[:, 0], pts[:, 1] - proj[:, 1])
        closer = dist < best_d
        best_d[closer] = dist[closer]
        best_s[closer] = s_start[i] + t[closer] * seg_len[i]
    return best_d, best_s


def _ray_arclength(poly: np.ndarray, origin: tuple[float, float], theta: float) -> float:
    """Arc length where a ray from ``origin`` at ``theta`` first leaves the polygon."""
    A, D, seg_len, s_start, perimeter = _segments(poly)
    ox, oy = origin
    rx, ry = float(np.cos(theta)), float(np.sin(theta))
    denom = rx * D[:, 1] - ry * D[:, 0]
    ok = np.abs(denom) > _EPS
    ax, ay = A[:, 0] - ox, A[:, 1] - oy
    with np.errstate(divide="ignore", invalid="ignore"):
        v = np.where(ok, (rx * ay - ry * ax) / denom, -1.0)  # along the segment
        t = (
            np.where(ok, (ax + v * D[:, 0]) / rx, -1.0)
            if abs(rx) > _EPS
            else np.where(ok, (ay + v * D[:, 1]) / ry, -1.0)
        )  # along the ray
    hit = ok & (v >= -1e-9) & (v <= 1 + 1e-9) & (t > 1e-9)
    if not hit.any():  # degenerate: nearest vertex
        return float(s_start[int(np.argmin(np.hypot(ax, ay)))])
    i = int(np.argmin(np.where(hit, t, np.inf)))
    return float(np.mod(s_start[i] + np.clip(v[i], 0.0, 1.0) * seg_len[i], perimeter))


def _extent_profile(
    s_k: np.ndarray, u_k: np.ndarray, perimeter: float, n: int = _PROFILE_SAMPLES
) -> tuple[np.ndarray, np.ndarray]:
    """Sample a periodic extent profile u(s) on a regular arc-length grid."""
    s_grid = np.linspace(0.0, perimeter, n, endpoint=False)
    order = np.argsort(s_k)
    s_sorted, u_sorted = s_k[order], u_k[order]
    # average readings that land on the same edge point
    keep_s, keep_u = [], []
    for s, u in zip(s_sorted, u_sorted):
        if keep_s and abs(s - keep_s[-1]) < 1e-6:
            keep_u[-1] = 0.5 * (keep_u[-1] + u)
        else:
            keep_s.append(float(s))
            keep_u.append(float(u))
    if len(keep_s) < 3:
        return s_grid, np.full(n, float(np.mean(keep_u)) if keep_u else 0.0)
    sp = np.array(keep_s + [keep_s[0] + perimeter])
    up = np.array(keep_u + [keep_u[0]])
    spline = CubicSpline(sp, up, bc_type="periodic")
    return s_grid, np.maximum(0.0, spline(np.mod(s_grid - sp[0], perimeter) + sp[0]))


def annulus_undermining(
    wound_edge_radius_mm: float, extent_mm: float, pocket_height_mm: float
) -> tuple[float, float]:
    """Closed-form undermined (area_mm2, volume_mm3) for a circular wound edge.

    ``A = pi((R + u)^2 - R^2)`` and ``V = A * h``. Provided as the analytic
    reference the raster implementation is checked against.
    """
    if wound_edge_radius_mm < 0 or extent_mm < 0 or pocket_height_mm < 0:
        raise ValueError("radius, extent and pocket height must be nonnegative")
    area = float(np.pi * ((wound_edge_radius_mm + extent_mm) ** 2 - wound_edge_radius_mm**2))
    return area, float(area * pocket_height_mm)


def integrate_undermining(
    measurements: Sequence[UnderminingMeasurement],
    wound_bed_depth_at_edge_mm: float = 0.0,
    *,
    wound_edge_radius_mm: float,
) -> tuple[float, float]:
    """Undermined ``(volume_mm3, area_mm2)`` for a wound treated as a circle.

    Integrates the annulus, ``A = integral (R u + u^2 / 2) dtheta``, with the
    extent splined in azimuth. ``wound_edge_radius_mm`` is required: without the
    wound's own size the undermined area is not defined, and omitting the
    ``R u`` term understates the result by ``1 + 2R/u``.

    Prefer :func:`compute_undermining`, which uses the real boundary polygon.
    """
    if wound_edge_radius_mm < 0:
        raise ValueError("wound_edge_radius_mm must be nonnegative")
    if not measurements:
        return 0.0, 0.0

    R, h = float(wound_edge_radius_mm), float(wound_bed_depth_at_edge_mm)
    thetas = np.array([_clock_to_theta(m.clock_position_hours) for m in measurements])
    extents = np.array([m.radial_extent_mm for m in measurements])
    order = np.argsort(thetas)
    thetas, extents = thetas[order], extents[order]

    if len(measurements) < 3:
        u = float(np.mean(extents))
        area, volume = annulus_undermining(R, u, h)
        return volume, area

    tp = np.concatenate([thetas, [thetas[0] + 2.0 * np.pi]])
    ep = np.concatenate([extents, [extents[0]]])
    spline = CubicSpline(tp, ep, bc_type="periodic")
    grid = np.linspace(tp[0], tp[-1], 360, endpoint=False)
    u = np.maximum(0.0, spline(grid))
    dtheta = 2.0 * np.pi / 360
    area = float(np.sum(R * u + 0.5 * u**2) * dtheta)
    return float(area * h), area


def compute_undermining(
    boundary_mm: Sequence[Sequence[float]],
    measurements: Sequence[UnderminingMeasurement],
    pocket_height_mm: float,
    *,
    pixel_size_mm: float = 0.25,
    extent_sigma_mm: float = 2.0,
    n_monte_carlo: int = 256,
    pocket_height_basis: str = "assumed equal to wound bed depth at the edge",
    rng: np.random.Generator | None = None,
) -> UnderminingResult:
    """Undermined area and volume from the wound boundary and probe extents.

    Parameters
    ----------
    boundary_mm : (N, 2)
        Wound edge polygon in the wound-local frame, in mm.
    measurements :
        Probe readings at clock positions. Fewer than three readings are
        treated as a uniform extent equal to their mean.
    pocket_height_mm :
        Assumed height of the undermined pocket. The probe does not measure it;
        whatever is passed here is echoed back in ``pocket_height_basis`` so the
        report can label the volume as assumption-dependent.
    pixel_size_mm :
        Raster pitch. 0.25 mm keeps the area discretisation error below ~0.1 %
        for wounds of clinical size.
    extent_sigma_mm :
        1-sigma probe-reading uncertainty used for the confidence interval.
        Set to 0 to disable the Monte Carlo pass.
    """
    poly = _as_open_polygon(boundary_mm)
    visible_area = polygon_area(poly)
    _, _, _, _, perimeter = _segments(poly)
    h = float(pocket_height_mm)
    if h < 0:
        raise ValueError("pocket_height_mm must be nonnegative")

    extents = np.array([m.radial_extent_mm for m in measurements], dtype=np.float64)
    clocks = np.array([m.clock_position_hours for m in measurements], dtype=np.float64)
    empty = (len(measurements) == 0) or bool(np.all(extents <= 0.0))
    if empty:
        return UnderminingResult(
            undermined_area_mm2=0.0,
            visible_area_mm2=visible_area,
            total_area_mm2=visible_area,
            undermined_volume_mm3=0.0,
            undermined_area_ci95_mm2=(0.0, 0.0),
            undermined_volume_ci95_mm3=(0.0, 0.0),
            max_extent_mm=0.0,
            max_extent_clock_hours=0.0,
            involved_clock_positions=(),
            pocket_height_mm=h,
            pocket_height_basis=pocket_height_basis,
            n_measurements=len(measurements),
            grid_pitch_mm=float(pixel_size_mm),
        )

    centroid = polygon_centroid(poly)
    s_k = np.array([_ray_arclength(poly, centroid, _clock_to_theta(c)) for c in clocks])

    # raster covering the boundary plus the largest plausible extent
    pad = float(extents.max() + 4.0 * max(extent_sigma_mm, 0.0) + 4.0 * pixel_size_mm)
    x0, y0 = poly[:, 0].min() - pad, poly[:, 1].min() - pad
    x1, y1 = poly[:, 0].max() + pad, poly[:, 1].max() + pad
    nx = max(int(np.ceil((x1 - x0) / pixel_size_mm)), 16)
    ny = max(int(np.ceil((y1 - y0) / pixel_size_mm)), 16)
    xs = x0 + (np.arange(nx) + 0.5) * pixel_size_mm
    ys = y0 + (np.arange(ny) + 0.5) * pixel_size_mm
    X, Y = np.meshgrid(xs, ys, indexing="xy")
    cell = pixel_size_mm * pixel_size_mm

    inside = _points_in_polygon(poly, X.ravel(), Y.ravel()).reshape(X.shape)
    out_idx = np.flatnonzero(~inside.ravel())
    pts = np.stack([X.ravel()[out_idx], Y.ravel()[out_idx]], axis=1)
    dist, s_near = _distance_and_arclength(poly, pts)

    s_grid, u_grid = _extent_profile(s_k, extents, perimeter)
    u_at = np.interp(s_near, s_grid, u_grid, period=perimeter)
    undermined_area = float(np.count_nonzero(dist <= u_at) * cell)

    lo_a = hi_a = undermined_area
    if n_monte_carlo > 0 and extent_sigma_mm > 0:
        gen = rng if rng is not None else np.random.default_rng(20260914)
        draws = np.empty(n_monte_carlo)
        for i in range(n_monte_carlo):
            pert = np.maximum(0.0, extents + gen.normal(0.0, extent_sigma_mm, size=extents.shape))
            _, ug = _extent_profile(s_k, pert, perimeter)
            draws[i] = (
                np.count_nonzero(dist <= np.interp(s_near, s_grid, ug, period=perimeter)) * cell
            )
        lo_a, hi_a = (float(v) for v in np.percentile(draws, [2.5, 97.5]))

    i_max = int(np.argmax(extents))
    involved = tuple(
        float(c) for c, u in sorted(zip(clocks, extents)) if u >= _INVOLVED_THRESHOLD_MM
    )
    return UnderminingResult(
        undermined_area_mm2=undermined_area,
        visible_area_mm2=visible_area,
        total_area_mm2=visible_area + undermined_area,
        undermined_volume_mm3=undermined_area * h,
        undermined_area_ci95_mm2=(lo_a, hi_a),
        undermined_volume_ci95_mm3=(lo_a * h, hi_a * h),
        max_extent_mm=float(extents[i_max]),
        max_extent_clock_hours=float(clocks[i_max]),
        involved_clock_positions=involved,
        pocket_height_mm=h,
        pocket_height_basis=pocket_height_basis,
        n_measurements=len(measurements),
        grid_pitch_mm=float(pixel_size_mm),
    )


def _points_in_polygon(poly: np.ndarray, px: np.ndarray, py: np.ndarray) -> np.ndarray:
    """Vectorised even-odd point-in-polygon test."""
    inside = np.zeros(px.shape, dtype=bool)
    x1, y1 = poly[:, 0], poly[:, 1]
    x2, y2 = np.roll(x1, -1), np.roll(y1, -1)
    for i in range(len(poly)):
        straddles = (y1[i] > py) != (y2[i] > py)
        if not straddles.any():
            continue
        dy = y2[i] - y1[i]
        if abs(dy) < _EPS:
            continue
        xint = x1[i] + (py - y1[i]) * (x2[i] - x1[i]) / dy
        inside ^= straddles & (px < xint)
    return inside
