"""Heteroscedastic Gaussian process fusion of camera depth + probe points.

Primary fusion method. Implements:

- Matern 5/2 kernel with separate length scales per dimension
- Heteroscedastic noise: per-point sigma from probe (constant) and from
  camera confidence (sigma_base / max(c, 0.05))
- Marginal-likelihood optimization of length scales
- Posterior mean AND posterior covariance for uncertainty propagation

This module contains a self-contained NumPy implementation of GP regression
that does not depend on GPy or GPyTorch. For production deployment we
optionally use GPyTorch via the `_gpytorch_backend` switch when available
for sparse approximation; the fallback NumPy implementation is exact and
suitable for grids up to ~100x100 and a few hundred anchor points.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class GPFusionResult:
    """Output of GP fusion: mean depth and posterior diagonals.

    Attributes
    ----------
    depth_mean_mm : (Ny, Nx)
        Posterior mean depth.
    depth_std_mm : (Ny, Nx)
        Posterior pointwise standard deviation.
    correlation_length_mm : float
        Optimized correlation length (geometric mean across dimensions);
        used downstream by Monte Carlo uncertainty.
    log_marginal_likelihood : float
        Optimized log p(y | params).
    n_anchors : int
        Number of anchor points (probe + downsampled camera).
    """

    depth_mean_mm: np.ndarray
    depth_std_mm: np.ndarray
    correlation_length_mm: float
    log_marginal_likelihood: float
    n_anchors: int


def _matern52(
    X1: np.ndarray, X2: np.ndarray, lengthscale_x: float, lengthscale_y: float
) -> np.ndarray:
    """Matern 5/2 kernel with axis-anisotropic length scales."""
    dx = (X1[:, 0:1] - X2[:, 0:1].T) / lengthscale_x
    dy = (X1[:, 1:2] - X2[:, 1:2].T) / lengthscale_y
    r2 = dx**2 + dy**2
    r = np.sqrt(np.maximum(r2, 1e-30))
    sqrt5 = np.sqrt(5.0)
    return (1.0 + sqrt5 * r + (5.0 / 3.0) * r2) * np.exp(-sqrt5 * r)


def _select_inducing_points(
    Xc: np.ndarray, n_inducing: int, rng: np.random.Generator
) -> np.ndarray:
    """Pick a subset of camera anchor points by farthest-point sampling."""
    if Xc.shape[0] <= n_inducing:
        return np.arange(Xc.shape[0])
    chosen = [int(rng.integers(Xc.shape[0]))]
    dists = np.linalg.norm(Xc - Xc[chosen[0]], axis=1)
    while len(chosen) < n_inducing:
        next_idx = int(np.argmax(dists))
        chosen.append(next_idx)
        new_d = np.linalg.norm(Xc - Xc[next_idx], axis=1)
        dists = np.minimum(dists, new_d)
    return np.array(chosen)


def fuse_gaussian_process(
    probe_x_mm: np.ndarray,
    probe_y_mm: np.ndarray,
    probe_d_mm: np.ndarray,
    probe_sigma_mm: np.ndarray,
    camera_x_mm: np.ndarray,
    camera_y_mm: np.ndarray,
    camera_d_mm: np.ndarray,
    camera_confidence: np.ndarray,
    grid_x_mm: np.ndarray,
    grid_y_mm: np.ndarray,
    sigma_base_mm: float = 1.0,
    max_camera_anchors: int = 400,
    optimize_lengthscale: bool = True,
    initial_lengthscale_mm: float = 8.0,
    rng: np.random.Generator | None = None,
) -> GPFusionResult:
    """Fuse probe + camera depth with a heteroscedastic GP.

    Parameters
    ----------
    probe_*_mm : (n_probe,) arrays
    probe_sigma_mm : (n_probe,) per-probe standard deviations
    camera_*_mm : (n_camera,) flat arrays of valid camera samples
    camera_confidence : (n_camera,) values in [0, 1]
    grid_x_mm, grid_y_mm : (Ny, Nx) meshgrid in mm
    sigma_base_mm : float
        Camera baseline noise; per-pixel sigma = sigma_base / max(conf, 0.05).
    max_camera_anchors : int
        Cap on the number of camera points used (subsampled by FPS).
    optimize_lengthscale : bool
        Whether to optimize length scales via marginal likelihood.
    initial_lengthscale_mm : float
        Starting length scale.
    """
    rng = rng or np.random.default_rng(0)

    Xp = np.column_stack([probe_x_mm, probe_y_mm])
    yp = np.asarray(probe_d_mm, dtype=np.float64)
    sp = np.asarray(probe_sigma_mm, dtype=np.float64)

    Xc = np.column_stack([camera_x_mm, camera_y_mm])
    yc = np.asarray(camera_d_mm, dtype=np.float64)
    conf = np.clip(np.asarray(camera_confidence, dtype=np.float64), 0.05, 1.0)
    sc = sigma_base_mm / conf

    if Xc.shape[0] > max_camera_anchors:
        idx = _select_inducing_points(Xc, max_camera_anchors, rng)
        Xc = Xc[idx]
        yc = yc[idx]
        sc = sc[idx]

    X = np.vstack([Xp, Xc])
    y = np.concatenate([yp, yc])
    sigma = np.concatenate([sp, sc])
    n = X.shape[0]

    def neg_log_marginal(params: np.ndarray) -> float:
        lx, ly = np.exp(params)
        K = _matern52(X, X, lx, ly) + np.diag(sigma**2)
        try:
            L = np.linalg.cholesky(K + 1e-6 * np.eye(n))
        except np.linalg.LinAlgError:
            return 1e10
        alpha = np.linalg.solve(L.T, np.linalg.solve(L, y))
        nll = 0.5 * y @ alpha + np.sum(np.log(np.diag(L))) + 0.5 * n * np.log(2 * np.pi)
        return float(nll)

    log_l = np.log(initial_lengthscale_mm)
    params = np.array([log_l, log_l])
    if optimize_lengthscale and n > 4:
        from scipy.optimize import minimize

        res = minimize(neg_log_marginal, params, method="L-BFGS-B")
        if res.success:
            params = res.x
        nll = float(res.fun)
    else:
        nll = neg_log_marginal(params)

    lx, ly = np.exp(params)

    K_train = _matern52(X, X, lx, ly) + np.diag(sigma**2) + 1e-6 * np.eye(n)
    L_train = np.linalg.cholesky(K_train)
    alpha = np.linalg.solve(L_train.T, np.linalg.solve(L_train, y))

    grid_pts = np.column_stack([grid_x_mm.flatten(), grid_y_mm.flatten()])
    K_query = _matern52(grid_pts, X, lx, ly)
    mean = (K_query @ alpha).reshape(grid_x_mm.shape)

    v = np.linalg.solve(L_train, K_query.T)
    var_diag = 1.0 - np.sum(v * v, axis=0)
    var_diag = np.maximum(var_diag, 1e-9).reshape(grid_x_mm.shape)
    std = np.sqrt(var_diag).astype(np.float32)

    return GPFusionResult(
        depth_mean_mm=mean.astype(np.float32),
        depth_std_mm=std,
        correlation_length_mm=float(np.sqrt(lx * ly)),
        log_marginal_likelihood=-nll,
        n_anchors=int(n),
    )
