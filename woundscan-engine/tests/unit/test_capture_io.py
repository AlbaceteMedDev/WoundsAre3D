"""Tests for capture/photo (load_photo) and capture/point_cloud (PLY I/O,
pose transform, color-mismatch + confidence-filter branches)."""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from woundscan.capture.depth_map import CameraIntrinsics, DepthFrame, load_depth_frame
from woundscan.capture.photo import PhotoFrame, load_photo
from woundscan.capture.point_cloud import PointCloud, depth_to_point_cloud, write_ply


def _intrinsics() -> CameraIntrinsics:
    return CameraIntrinsics(fx=500.0, fy=500.0, cx=320.0, cy=240.0, width=640, height=480)


def _depth_frame(h: int = 16, w: int = 16, depth_m: float = 0.30) -> DepthFrame:
    depth = np.full((h, w), depth_m, dtype=np.float32)
    conf = np.full((h, w), 2, dtype=np.uint8)
    K = CameraIntrinsics(fx=500.0, fy=500.0, cx=w / 2.0, cy=h / 2.0, width=w, height=h)
    return load_depth_frame(depth, conf, K, timestamp_s=0.0)


# ---------------------------------------------------------------------------
# photo
# ---------------------------------------------------------------------------


class TestLoadPhoto:
    def test_from_ndarray_uint8(self):
        rgb = np.full((10, 10, 3), 128, dtype=np.uint8)
        frame = load_photo(rgb, _intrinsics(), timestamp_s=1.0)
        assert isinstance(frame, PhotoFrame)
        assert frame.rgb.dtype == np.uint8
        assert frame.timestamp_s == 1.0

    def test_from_ndarray_float_rescaled(self):
        rgb = np.full((10, 10, 3), 0.5, dtype=np.float32)
        frame = load_photo(rgb, _intrinsics(), timestamp_s=0.0)
        assert frame.rgb.dtype == np.uint8
        assert frame.rgb[0, 0, 0] == 127  # 0.5 * 255 = 127.5 → 127 after truncation

    def test_from_bytes(self):
        img = Image.new("RGB", (8, 8), (100, 50, 25))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        frame = load_photo(buf.getvalue(), _intrinsics(), timestamp_s=0.0)
        assert frame.rgb.shape == (8, 8, 3)
        assert tuple(frame.rgb[0, 0]) == (100, 50, 25)

    def test_from_file_path(self, tmp_path: Path):
        img = Image.new("RGB", (4, 4), (200, 0, 0))
        p = tmp_path / "frame.png"
        img.save(p)
        frame = load_photo(str(p), _intrinsics(), timestamp_s=0.0)
        assert frame.rgb.shape == (4, 4, 3)
        assert frame.rgb[0, 0, 0] == 200

    def test_unsupported_type_raises(self):
        with pytest.raises(TypeError):
            load_photo(123, _intrinsics(), timestamp_s=0.0)  # type: ignore[arg-type]

    def test_rejects_wrong_dimensionality(self):
        bad = np.zeros((10, 10), dtype=np.uint8)
        with pytest.raises(ValueError):
            PhotoFrame(
                rgb=bad,
                intrinsics=_intrinsics(),
                timestamp_s=0.0,
                iso=100,
                shutter_speed_s=1 / 60,
                aperture=1.8,
                focal_length_mm=5.96,
            )

    def test_rejects_wrong_dtype(self):
        bad = np.zeros((4, 4, 3), dtype=np.float32)
        with pytest.raises(ValueError):
            PhotoFrame(
                rgb=bad,
                intrinsics=_intrinsics(),
                timestamp_s=0.0,
                iso=100,
                shutter_speed_s=1 / 60,
                aperture=1.8,
                focal_length_mm=5.96,
            )


# ---------------------------------------------------------------------------
# point_cloud
# ---------------------------------------------------------------------------


class TestDepthToPointCloud:
    def test_camera_frame_when_no_pose(self):
        frame = _depth_frame()
        pc = depth_to_point_cloud(frame)
        assert pc.frame == "camera"
        assert pc.colors is None

    def test_with_rgb_emits_colors(self):
        h, w = 16, 16
        frame = _depth_frame(h=h, w=w)
        rgb = np.full((h, w, 3), 80, dtype=np.uint8)
        pc = depth_to_point_cloud(frame, rgb=rgb)
        assert pc.colors is not None
        assert pc.colors.shape[1] == 3
        assert np.all(pc.colors == 80)

    def test_with_pose_transforms_to_world(self):
        frame = _depth_frame()
        # Translate by +1m along x; world frame should reflect that.
        pose = np.eye(4)
        pose[0, 3] = 1.0
        pc = depth_to_point_cloud(frame, pose_4x4=pose)
        assert pc.frame == "world"
        assert pc.points_m[:, 0].min() >= 1.0 - 0.5

    def test_rejects_wrong_pose_shape(self):
        frame = _depth_frame()
        with pytest.raises(ValueError):
            depth_to_point_cloud(frame, pose_4x4=np.eye(3))

    def test_rejects_rgb_shape_mismatch(self):
        frame = _depth_frame(h=16, w=16)
        rgb = np.full((8, 8, 3), 80, dtype=np.uint8)
        with pytest.raises(ValueError):
            depth_to_point_cloud(frame, rgb=rgb)

    def test_low_confidence_returns_empty_cloud(self):
        # All confidences below threshold → empty cloud, no exception.
        depth = np.full((4, 4), 0.3, dtype=np.float32)
        conf = np.zeros((4, 4), dtype=np.uint8)  # all 0
        K = CameraIntrinsics(fx=100.0, fy=100.0, cx=2.0, cy=2.0, width=4, height=4)
        frame = load_depth_frame(depth, conf, K, timestamp_s=0.0)
        pc = depth_to_point_cloud(frame, min_confidence=2)
        assert pc.points_m.shape == (0, 3)
        assert pc.colors is None
        assert pc.frame == "camera"

    def test_low_confidence_empty_with_rgb_emits_empty_colors(self):
        # Empty path with rgb provided → still returns shape (0, 3) colors.
        depth = np.full((4, 4), 0.3, dtype=np.float32)
        conf = np.zeros((4, 4), dtype=np.uint8)
        K = CameraIntrinsics(fx=100.0, fy=100.0, cx=2.0, cy=2.0, width=4, height=4)
        frame = load_depth_frame(depth, conf, K, timestamp_s=0.0)
        rgb = np.full((4, 4, 3), 200, dtype=np.uint8)
        pc = depth_to_point_cloud(frame, rgb=rgb, min_confidence=2)
        assert pc.points_m.shape == (0, 3)
        assert pc.colors is not None
        assert pc.colors.shape == (0, 3)


class TestWritePLY:
    def test_round_trip_without_colors(self, tmp_path: Path):
        pc = PointCloud(
            points_m=np.array([[0.0, 0.0, 0.0], [1.0, 2.0, 3.0]]),
            colors=None,
            frame="camera",
        )
        path = tmp_path / "out.ply"
        write_ply(pc, str(path))
        text = path.read_text()
        assert text.startswith("ply\n")
        assert "element vertex 2" in text
        assert "1.000000 2.000000 3.000000" in text
        # No color properties when colors is None.
        assert "property uchar red" not in text

    def test_round_trip_with_colors(self, tmp_path: Path):
        pc = PointCloud(
            points_m=np.array([[0.0, 0.0, 0.0]]),
            colors=np.array([[255, 128, 0]], dtype=np.uint8),
            frame="world",
        )
        path = tmp_path / "out.ply"
        write_ply(pc, str(path))
        text = path.read_text()
        assert "property uchar red" in text
        assert "0.000000 0.000000 0.000000 255 128 0" in text

    def test_pointcloud_len_dunder(self):
        pc = PointCloud(
            points_m=np.zeros((7, 3)), colors=None, frame="camera"
        )
        assert len(pc) == 7
