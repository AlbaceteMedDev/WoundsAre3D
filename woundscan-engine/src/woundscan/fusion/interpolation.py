"""Thin-plate spline interpolation through anchor points.

A baseline interpolant for the fused depth field. The TPS minimizes
bending energy subject to interpolating the data, producing a smooth
surface through the (probe + camera) measurements.

This is the FALLBACK fusion method, used when the Gaussian process is
not available (e.g., insufficient compute, missing GPyTorch). It does
NOT produce uncertainty estimates — for that, use `fuse_gaussian_process`.
"""

from __future__ import annotations

import numpy as np


def thin_plate_spline(
    x_anchors_mm: np.ndarray,
    y_anchors_mm: np.ndarray,
    d_anchors_mm: np.ndarray,
    xq_mm: np.ndarray,
    yq_mm: np.ndarray,
    regularization: float = 1e-6,
) -> np.ndarray:
    """Thin-plate spline interpolation.

    Parameters
    ----------
    x_anchors_mm, y_anchors_mm, d_anchors_mm : (N,) arrays
        Anchor point coordinates and depth values.
    xq_mm, yq_mm : (M,) or (Ny, Nx) arrays
        Query points where the spline is evaluated. Shape is preserved.
    regularization : float
        Ridge term added to the kernel matrix for numerical stability.

    Returns
    -------
    d_query_mm : same shape as xq_mm
    """
    x = np.asarray(x_anchors_mm, dtype=np.float64).flatten()
    y = np.asarray(y_anchors_mm, dtype=np.float64).flatten()
    d = np.asarray(d_anchors_mm, dtype=np.float64).flatten()
    if x.shape != y.shape or x.shape != d.shape:
        raise ValueError("anchor arrays must have the same length")
    if x.size < 3:
        raise ValueError("Need at least 3 anchor points for TPS")

    n = x.size

    def U(r2: np.ndarray) -> np.ndarray:
        return np.where(r2 > 0, r2 * np.log(np.sqrt(r2) + 1e-12), 0.0)

    dx = x[:, None] - x[None, :]
    dy = y[:, None] - y[None, :]
    K = U(dx**2 + dy**2)
    K = K + regularization * np.eye(n)

    P = np.column_stack([np.ones(n), x, y])
    L_top = np.column_stack([K, P])
    L_bot = np.column_stack([P.T, np.zeros((3, 3))])
    L = np.vstack([L_top, L_bot])
    rhs = np.concatenate([d, np.zeros(3)])
    sol = np.linalg.solve(L, rhs)
    w = sol[:n]
    a = sol[n:]

    qx = np.asarray(xq_mm, dtype=np.float64)
    qy = np.asarray(yq_mm, dtype=np.float64)
    orig_shape = qx.shape
    qx_flat = qx.flatten()
    qy_flat = qy.flatten()
    dxq = qx_flat[:, None] - x[None, :]
    dyq = qy_flat[:, None] - y[None, :]
    Kq = U(dxq**2 + dyq**2)
    out = Kq @ w + a[0] + a[1] * qx_flat + a[2] * qy_flat
    return out.reshape(orig_shape)
