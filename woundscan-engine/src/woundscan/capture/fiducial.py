"""ArUco fiducial detection and pose recovery.

The clinician places a printed sticker with 4 ArUco markers (5x5 dictionary)
arranged at the corners of a known-size square adjacent to the wound. We
detect the markers, recover the marker-to-camera pose, and use this to:

1. Provide an absolute scale check (the marker size is known in mm)
2. Define a wound-local coordinate frame anchored to the patient
3. Cross-check ARKit pose drift across the burst capture
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class FiducialDetection:
    """A single ArUco marker detected in an image.

    Attributes
    ----------
    marker_id : int
        ArUco dictionary ID.
    corners_pix : (4, 2) array
        Image-space corner positions (clockwise from top-left).
    rvec : (3,) array
        Rodrigues rotation vector, marker-to-camera.
    tvec : (3,) array
        Translation vector in meters, marker-to-camera.
    reprojection_error_pix : float
    """

    marker_id: int
    corners_pix: np.ndarray
    rvec: np.ndarray
    tvec: np.ndarray
    reprojection_error_pix: float


def detect_aruco(
    rgb: np.ndarray,
    intrinsic_matrix: np.ndarray,
    marker_side_mm: float,
    dist_coeffs: np.ndarray | None = None,
    dictionary: str = "DICT_5X5_50",
) -> list[FiducialDetection]:
    """Detect ArUco markers and recover per-marker pose.

    Parameters
    ----------
    rgb : (H, W, 3) uint8
    intrinsic_matrix : (3, 3)
    marker_side_mm : float
        Physical side length of each marker.
    dist_coeffs : (5,) or (8,), optional
        Lens distortion coefficients. Defaults to zero distortion.
    dictionary : str
        OpenCV ArUco dictionary name.
    """
    try:
        import cv2
    except ImportError as e:
        raise RuntimeError("OpenCV required for ArUco detection") from e

    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError(f"rgb must be (H, W, 3), got {rgb.shape}")
    if dist_coeffs is None:
        dist_coeffs = np.zeros((5,), dtype=np.float64)

    aruco_dict = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, dictionary))
    parameters = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    corners, ids, _ = detector.detectMarkers(gray)
    if ids is None or len(ids) == 0:
        return []

    results: list[FiducialDetection] = []
    side_m = marker_side_mm * 0.001
    obj_pts = np.array(
        [
            [-side_m / 2, side_m / 2, 0.0],
            [side_m / 2, side_m / 2, 0.0],
            [side_m / 2, -side_m / 2, 0.0],
            [-side_m / 2, -side_m / 2, 0.0],
        ],
        dtype=np.float64,
    )
    for marker_corners, marker_id in zip(corners, ids.flatten(), strict=False):
        img_pts = marker_corners.reshape(-1, 2).astype(np.float64)
        ok, rvec, tvec = cv2.solvePnP(
            obj_pts,
            img_pts,
            intrinsic_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_IPPE_SQUARE,
        )
        if not ok:
            continue
        proj, _ = cv2.projectPoints(obj_pts, rvec, tvec, intrinsic_matrix, dist_coeffs)
        err = float(np.mean(np.linalg.norm(proj.reshape(-1, 2) - img_pts, axis=1)))
        results.append(
            FiducialDetection(
                marker_id=int(marker_id),
                corners_pix=img_pts,
                rvec=rvec.flatten().astype(np.float64),
                tvec=tvec.flatten().astype(np.float64),
                reprojection_error_pix=err,
            )
        )
    return results


def compute_scale_check(
    detections: list[FiducialDetection],
    expected_marker_separation_mm: float,
    *,
    tolerance: float = 0.02,
) -> tuple[bool, float]:
    """Verify that physical scale recovered from markers matches expectation.

    With 4 markers placed at known positions, distances between markers
    in 3D should match the known separation. Compute mean recovered
    separation and compare to expected.

    Returns (passed, relative_error).
    """
    if len(detections) < 2:
        return False, float("inf")

    centers = np.array([d.tvec for d in detections])
    if centers.shape[0] < 2:
        return False, float("inf")

    dists_mm = []
    for i in range(centers.shape[0]):
        for j in range(i + 1, centers.shape[0]):
            d_m = float(np.linalg.norm(centers[i] - centers[j]))
            dists_mm.append(d_m * 1000.0)
    mean_d = float(np.mean(dists_mm))
    rel = abs(mean_d - expected_marker_separation_mm) / expected_marker_separation_mm
    return rel <= tolerance, rel
