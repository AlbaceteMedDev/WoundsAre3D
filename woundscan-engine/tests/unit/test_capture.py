"""Tests for capture: depth_map, point_cloud, multiframe, photo, polarization."""
import numpy as np
import pytest

from woundscan.capture.depth_map import CameraIntrinsics, DepthFrame, load_depth_frame
from woundscan.capture.multiframe import temporal_average_depth
from woundscan.capture.point_cloud import depth_to_point_cloud
from woundscan.capture.polarization import PolarizedCapture, extract_diffuse_specular


def _intrinsics() -> CameraIntrinsics:
    return CameraIntrinsics(fx=500.0, fy=500.0, cx=320.0, cy=240.0, width=640, height=480)


class TestDepthFrame:
    def test_load_converts_meters_to_cm(self):
        depth_m = np.full((10, 10), 0.5, dtype=np.float32)
        conf = np.full((10, 10), 2, dtype=np.uint8)
        frame = load_depth_frame(depth_m, conf, _intrinsics(), timestamp_s=0.0)
        assert frame.depth_cm[0, 0] == pytest.approx(50.0)

    def test_filtered_depth_masks_low_confidence(self):
        depth_m = np.full((10, 10), 0.5, dtype=np.float32)
        conf = np.zeros((10, 10), dtype=np.uint8)
        conf[5:, :] = 2
        frame = load_depth_frame(depth_m, conf, _intrinsics(), 0.0)
        filtered = frame.filtered_depth(min_confidence=1)
        assert np.isnan(filtered[0, 0])
        assert not np.isnan(filtered[5, 0])


class TestPointCloud:
    def test_projects_to_3d(self):
        depth_m = np.full((20, 20), 0.5, dtype=np.float32)
        conf = np.full((20, 20), 2, dtype=np.uint8)
        K = CameraIntrinsics(fx=100.0, fy=100.0, cx=10.0, cy=10.0, width=20, height=20)
        frame = load_depth_frame(depth_m, conf, K, timestamp_s=0.0)
        pc = depth_to_point_cloud(frame)
        assert len(pc) == 400
        assert pc.frame == "camera"


class TestMultiframe:
    def test_temporal_average_reduces_noise(self):
        rng = np.random.default_rng(0)
        intr = _intrinsics()
        frames = []
        for _ in range(20):
            d = (np.full((10, 10), 0.5) + rng.normal(scale=0.01, size=(10, 10))).astype(np.float32)
            c = np.full((10, 10), 2, dtype=np.uint8)
            frames.append(load_depth_frame(d, c, intr, timestamp_s=0.0))

        avg, std, n = temporal_average_depth(frames)
        # Average should be ~50cm, std small
        assert abs(np.mean(avg) - 50.0) < 0.5
        assert np.mean(std) < 1.0
        assert (n > 10).all()


class TestPolarization:
    def test_diffuse_specular_decomposition(self):
        cross = np.full((20, 20, 3), 100, dtype=np.uint8)
        parallel = np.full((20, 20, 3), 150, dtype=np.uint8)
        cap = PolarizedCapture(cross_polarized=cross, parallel_polarized=parallel)
        diff, spec = extract_diffuse_specular(cap)
        assert (diff == 100).all()
        assert (spec == 50).all()
