"""Point cloud generation and PLY I/O.

Project depth pixels through camera intrinsics into world coordinates,
build a (N, 3) point cloud. Used by bundle adjustment, fiducial pose
recovery, and PLY archival for review.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from woundscan.capture.depth_map import DepthFrame


@dataclass(frozen=True)
class PointCloud:
    """A 3D point cloud in a named frame."""

    points_m: np.ndarray  # (N, 3) in meters
    colors: np.ndarray | None  # (N, 3) uint8 RGB; None if no color
    frame: str

    def __len__(self) -> int:
        return int(self.points_m.shape[0])


def depth_to_point_cloud(
    frame: DepthFrame,
    rgb: np.ndarray | None = None,
    pose_4x4: np.ndarray | None = None,
    min_confidence: int = 1,
) -> PointCloud:
    """Project a depth frame to a 3D point cloud.

    Parameters
    ----------
    frame : DepthFrame
    rgb : (H, W, 3), optional
        Color image of same resolution; defaults to no color.
    pose_4x4 : (4, 4), optional
        Camera-to-world transform. If None, points are in camera frame.
    min_confidence : int
        Minimum ARKit depth confidence (0..2) to include.
    """
    K = frame.intrinsics.to_matrix()
    h, w = frame.depth_cm.shape
    valid = (frame.confidence >= min_confidence) & np.isfinite(frame.depth_cm)
    if not valid.any():
        return PointCloud(
            points_m=np.zeros((0, 3), dtype=np.float64),
            colors=None if rgb is None else np.zeros((0, 3), dtype=np.uint8),
            frame="camera" if pose_4x4 is None else "world",
        )

    yy, xx = np.indices((h, w))
    z_m = frame.depth_cm[valid] / 100.0
    x_pix = xx[valid].astype(np.float64)
    y_pix = yy[valid].astype(np.float64)
    x_m = (x_pix - K[0, 2]) * z_m / K[0, 0]
    y_m = (y_pix - K[1, 2]) * z_m / K[1, 1]
    pts = np.stack([x_m, y_m, z_m], axis=1)

    if pose_4x4 is not None:
        if pose_4x4.shape != (4, 4):
            raise ValueError(f"pose must be 4x4, got {pose_4x4.shape}")
        homog = np.concatenate([pts, np.ones((pts.shape[0], 1))], axis=1)
        world = (pose_4x4 @ homog.T).T[:, :3]
        pts = world

    colors_out = None
    if rgb is not None:
        if rgb.shape[:2] != (h, w):
            raise ValueError(f"rgb shape {rgb.shape[:2]} doesn't match depth shape ({h}, {w})")
        colors_out = rgb[valid].astype(np.uint8)

    return PointCloud(
        points_m=pts,
        colors=colors_out,
        frame="camera" if pose_4x4 is None else "world",
    )


def write_ply(point_cloud: PointCloud, path: str) -> None:
    """Write a point cloud to PLY (ASCII)."""
    pts = point_cloud.points_m
    colors = point_cloud.colors
    n = pts.shape[0]
    with open(path, "w") as f:
        f.write("ply\nformat ascii 1.0\n")
        f.write(f"element vertex {n}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        if colors is not None:
            f.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
        f.write("end_header\n")
        if colors is not None:
            for (x, y, z), (r, g, b) in zip(pts, colors, strict=True):
                f.write(f"{x:.6f} {y:.6f} {z:.6f} {int(r)} {int(g)} {int(b)}\n")
        else:
            for x, y, z in pts:
                f.write(f"{x:.6f} {y:.6f} {z:.6f}\n")
