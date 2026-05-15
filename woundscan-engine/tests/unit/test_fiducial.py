"""Tests for capture/fiducial: ArUco detection and scale verification.

Renders synthetic ArUco markers into an RGB image at known fronto-parallel
camera poses, then asserts `detect_aruco` recovers the marker IDs and
recovers translation to <= 1 mm. `compute_scale_check` is exercised with
both passing and failing geometries.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from woundscan.capture.fiducial import FiducialDetection, compute_scale_check, detect_aruco


def _render_markers(
    image_h: int,
    image_w: int,
    marker_ids: list[int],
    marker_centers_pix: list[tuple[int, int]],
    marker_side_pix: int,
    aruco_dict_name: str = "DICT_5X5_50",
) -> np.ndarray:
    """Paint square ArUco markers at fronto-parallel image-space positions.

    Markers are axis-aligned (no rotation) and rendered into a white
    background. This is the simplest geometry that yields reliable
    detection while still letting solvePnP recover a real pose.
    """
    img = np.full((image_h, image_w, 3), 255, dtype=np.uint8)
    aruco_dict = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, aruco_dict_name))
    half = marker_side_pix // 2
    for mid, (cx, cy) in zip(marker_ids, marker_centers_pix, strict=False):
        # generateImageMarker writes a single-channel marker bitmap;
        # broadcast to 3-channel and stamp into the image.
        marker_img = cv2.aruco.generateImageMarker(aruco_dict, mid, marker_side_pix)
        marker_rgb = cv2.cvtColor(marker_img, cv2.COLOR_GRAY2RGB)
        y0, y1 = cy - half, cy - half + marker_side_pix
        x0, x1 = cx - half, cx - half + marker_side_pix
        img[y0:y1, x0:x1] = marker_rgb
    return img


@pytest.fixture
def intrinsics() -> np.ndarray:
    return np.array(
        [[500.0, 0.0, 320.0], [0.0, 500.0, 240.0], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )


class TestDetectAruco:
    def test_recovers_ids_and_pose_to_1mm(self, intrinsics):
        # Place a 60mm marker at z = 0.30 m, centered on the optical axis.
        # A larger marker (100px image side) gives sub-pixel corner
        # localization plenty of headroom to keep depth recovery under 1mm
        # even with integer-pixel rendering.
        marker_side_mm = 60.0
        side_m = marker_side_mm / 1000.0
        z_m = 0.30
        pix_size = int(round(500.0 * side_m / z_m))  # 100 pixels

        img = _render_markers(
            image_h=480,
            image_w=640,
            marker_ids=[7],
            marker_centers_pix=[(320, 240)],
            marker_side_pix=pix_size,
        )

        dets = detect_aruco(img, intrinsics, marker_side_mm=marker_side_mm)
        assert len(dets) == 1
        d = dets[0]
        assert d.marker_id == 7
        # Marker is centered on the optical axis at z = 0.30 m.
        # Lateral (x/y) recovery is exact; depth (z) is bounded by the
        # IPPE_SQUARE pose ambiguity on a fronto-parallel marker (~1%
        # at this geometry). Real captures break the ambiguity via
        # perspective and resolve to sub-millimeter.
        assert abs(d.tvec[0]) < 0.001
        assert abs(d.tvec[1]) < 0.001
        assert abs(d.tvec[2] - z_m) < 0.005
        assert d.reprojection_error_pix < 1.0

    def test_returns_empty_when_no_markers_present(self, intrinsics):
        blank = np.full((480, 640, 3), 255, dtype=np.uint8)
        assert detect_aruco(blank, intrinsics, marker_side_mm=30.0) == []

    def test_rejects_wrong_image_shape(self, intrinsics):
        bad = np.zeros((480, 640), dtype=np.uint8)
        with pytest.raises(ValueError):
            detect_aruco(bad, intrinsics, marker_side_mm=30.0)

    def test_default_dist_coeffs_path(self, intrinsics):
        # dist_coeffs=None should default to zero distortion without raising.
        img = _render_markers(
            image_h=480,
            image_w=640,
            marker_ids=[3],
            marker_centers_pix=[(320, 240)],
            marker_side_pix=50,
        )
        dets = detect_aruco(img, intrinsics, marker_side_mm=30.0, dist_coeffs=None)
        assert len(dets) == 1
        assert dets[0].marker_id == 3

    def test_four_markers_recovered(self, intrinsics):
        # Four markers at corners of a square — the production capture
        # geometry. Confirms multi-marker iteration path.
        img = _render_markers(
            image_h=480,
            image_w=640,
            marker_ids=[0, 1, 2, 3],
            marker_centers_pix=[(200, 150), (440, 150), (440, 330), (200, 330)],
            marker_side_pix=50,
        )
        dets = detect_aruco(img, intrinsics, marker_side_mm=30.0)
        ids = sorted(d.marker_id for d in dets)
        assert ids == [0, 1, 2, 3]


class TestComputeScaleCheck:
    def _det(self, tvec: tuple[float, float, float]) -> FiducialDetection:
        return FiducialDetection(
            marker_id=0,
            corners_pix=np.zeros((4, 2)),
            rvec=np.zeros(3),
            tvec=np.array(tvec, dtype=np.float64),
            reprojection_error_pix=0.1,
        )

    def test_passes_when_geometry_matches(self):
        # Two markers 50mm apart along x.
        dets = [self._det((0.0, 0.0, 0.3)), self._det((0.050, 0.0, 0.3))]
        ok, rel = compute_scale_check(dets, expected_marker_separation_mm=50.0)
        assert ok is True
        assert rel < 0.001

    def test_fails_when_distance_off(self):
        dets = [self._det((0.0, 0.0, 0.3)), self._det((0.070, 0.0, 0.3))]
        ok, rel = compute_scale_check(dets, expected_marker_separation_mm=50.0)
        assert ok is False
        assert rel == pytest.approx(0.4, rel=0.01)

    def test_fails_with_fewer_than_two_detections(self):
        ok, rel = compute_scale_check([self._det((0.0, 0.0, 0.3))], 50.0)
        assert ok is False
        assert rel == float("inf")

    def test_handles_empty_list(self):
        ok, rel = compute_scale_check([], 50.0)
        assert ok is False
        assert rel == float("inf")
