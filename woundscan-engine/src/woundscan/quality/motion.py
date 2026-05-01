"""Motion artifact detection from frame-to-frame ARKit pose deltas."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CameraPose:
    """6-DoF camera pose: position in meters, rotation as quaternion (x, y, z, w)."""

    position_m: tuple[float, float, float]
    rotation_quat: tuple[float, float, float, float]
    timestamp_s: float


def _quat_dot(q1: tuple[float, ...], q2: tuple[float, ...]) -> float:
    return sum(a * b for a, b in zip(q1, q2, strict=True))


def _angular_delta_deg(q1: tuple[float, ...], q2: tuple[float, ...]) -> float:
    """Angle between two unit quaternions, in degrees."""
    d = _quat_dot(q1, q2)
    d = max(-1.0, min(1.0, abs(d)))
    return float(np.degrees(2.0 * np.arccos(d)))


def compute_motion_artifact(
    poses: list[CameraPose],
    image_shape: tuple[int, int],
    *,
    translation_threshold_mm: float = 5.0,
    rotation_threshold_deg: float = 2.0,
) -> np.ndarray:
    """Per-pixel motion artifact in [0, 1]; lower = sharper.

    For an in-app capture burst, we compare consecutive poses; if motion
    between frames is large, the contributing frames are blurred. We
    return a uniform score across the image based on the worst frame
    transition (motion blur is approximately spatially uniform for
    handheld capture, dominated by global rather than parallax motion).
    """
    if len(poses) < 2:
        return np.zeros(image_shape, dtype=np.float32)

    max_t_mm = 0.0
    max_r_deg = 0.0
    for p1, p2 in zip(poses[:-1], poses[1:], strict=False):
        dt = max(p2.timestamp_s - p1.timestamp_s, 1e-3)
        translation_mm = (
            np.linalg.norm(np.subtract(p2.position_m, p1.position_m)) * 1000.0 / dt
        )
        rotation_deg = _angular_delta_deg(p1.rotation_quat, p2.rotation_quat) / dt
        max_t_mm = max(max_t_mm, float(translation_mm))
        max_r_deg = max(max_r_deg, float(rotation_deg))

    t_score = min(1.0, max_t_mm / translation_threshold_mm)
    r_score = min(1.0, max_r_deg / rotation_threshold_deg)
    score = max(t_score, r_score)
    return np.full(image_shape, score, dtype=np.float32)
