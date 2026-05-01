"""Bayesian temporal fusion across visits via Kalman filtering.

State: x = (V, S, h_max, dV/dt, dS/dt, dh/dt) in cm^3, cm^2, cm.
Process model: constant-velocity (wounds heal at approximately stable
rate over short windows) with process noise reflecting expected
biological variability.

Observation model: z_t = H x_t + v_t, where H projects state to
(V, S, h_max) and v_t has covariance equal to the GP-derived
measurement uncertainty.

Outlier flagging: measurements that are >3-sigma from the predicted
state are tagged for clinician review (not auto-rejected).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class TemporalState:
    """6D Kalman state (V, S, h_max, dV/dt, dS/dt, dh/dt) and covariance."""

    mean: np.ndarray  # (6,)
    cov: np.ndarray  # (6, 6)
    timestamp_s: float


@dataclass(frozen=True)
class TemporalUpdate:
    """Result of a single Kalman update step."""

    posterior: TemporalState
    innovation: np.ndarray  # (3,)
    innovation_cov: np.ndarray  # (3, 3)
    is_outlier: bool


_SECONDS_PER_DAY = 86400.0


def _process_model_F(dt_days: float) -> np.ndarray:
    """Constant-velocity transition matrix. dt is in DAYS (rates are per-day)."""
    F = np.eye(6)
    F[0, 3] = dt_days
    F[1, 4] = dt_days
    F[2, 5] = dt_days
    return F


def _process_noise_Q(
    dt_days: float,
    q_volume: float = 0.01,
    q_area: float = 0.05,
    q_depth: float = 0.005,
) -> np.ndarray:
    """Process noise covariance. q_* are per-day variance rates of CHANGE rate.

    For a constant-velocity model, the standard discretization is:
        Q = G * Q_acc * G^T
    where G = [[0.5*dt^2], [dt]] for each (position, velocity) pair.
    """
    q = np.array([q_volume, q_area, q_depth])
    G = np.zeros((6, 3))
    G[0, 0] = 0.5 * dt_days**2
    G[3, 0] = dt_days
    G[1, 1] = 0.5 * dt_days**2
    G[4, 1] = dt_days
    G[2, 2] = 0.5 * dt_days**2
    G[5, 2] = dt_days
    Q_acc = np.diag(q)
    return G @ Q_acc @ G.T


def kalman_update(
    prior: TemporalState,
    z_volume: float,
    z_area: float,
    z_depth: float,
    R_meas: np.ndarray,  # (3, 3) measurement covariance
    new_timestamp_s: float,
    outlier_sigma: float = 3.0,
) -> TemporalUpdate:
    """Predict-update step of the Kalman filter.

    Parameters
    ----------
    prior : TemporalState
        State and covariance from the previous visit.
    z_volume, z_area, z_depth : float
        Current measurement.
    R_meas : (3, 3)
        Measurement covariance from GP fusion uncertainty.
    new_timestamp_s : float
    outlier_sigma : float
        Mahalanobis distance threshold for outlier flagging.
    """
    dt_s = max(new_timestamp_s - prior.timestamp_s, 1.0)
    dt_days = dt_s / _SECONDS_PER_DAY
    F = _process_model_F(dt_days)
    Q = _process_noise_Q(dt_days)

    pred_mean = F @ prior.mean
    pred_cov = F @ prior.cov @ F.T + Q

    H = np.zeros((3, 6))
    H[0, 0] = 1.0
    H[1, 1] = 1.0
    H[2, 2] = 1.0
    z = np.array([z_volume, z_area, z_depth])

    innovation = z - H @ pred_mean
    S = H @ pred_cov @ H.T + R_meas
    K = pred_cov @ H.T @ np.linalg.inv(S)

    post_mean = pred_mean + K @ innovation
    post_cov = (np.eye(6) - K @ H) @ pred_cov

    mahal = float(innovation @ np.linalg.solve(S, innovation))
    is_outlier = mahal > outlier_sigma**2

    return TemporalUpdate(
        posterior=TemporalState(mean=post_mean, cov=post_cov, timestamp_s=new_timestamp_s),
        innovation=innovation,
        innovation_cov=S,
        is_outlier=is_outlier,
    )


def initialize_temporal_state(
    initial_volume: float,
    initial_area: float,
    initial_depth: float,
    initial_uncertainty: tuple[float, float, float],
    timestamp_s: float,
) -> TemporalState:
    """Bootstrap state from the first measurement.

    Initial velocities are zero with high uncertainty.
    """
    mean = np.array([initial_volume, initial_area, initial_depth, 0.0, 0.0, 0.0])
    cov = np.diag(
        [
            initial_uncertainty[0] ** 2,
            initial_uncertainty[1] ** 2,
            initial_uncertainty[2] ** 2,
            (initial_volume * 0.5) ** 2,
            (initial_area * 0.5) ** 2,
            (initial_depth * 0.5) ** 2,
        ]
    )
    return TemporalState(mean=mean, cov=cov, timestamp_s=timestamp_s)
