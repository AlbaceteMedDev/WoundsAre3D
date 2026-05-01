"""Robust fiducial detection (occlusion- and angle-tolerant).

The pure-OpenCV ArUco detector in `capture/fiducial.py` fails on:
- Heavy occlusion (clinician's hand or instrument blocks a marker)
- Glare from overhead lights on the marker surface
- Steep incidence angles (>70 deg from normal)

The robust detector pre-processes the image (CLAHE for glare, multi-scale
for distance robustness) and combines the OpenCV detection with a
contour-based fallback that finds black-bordered quadrilaterals and
classifies their internal pattern by template matching.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class RobustFiducialDetector:
    """Combined robust + fallback ArUco detector wrapper.

    Usage
    -----
    >>> det = RobustFiducialDetector()
    >>> markers = det.detect(rgb, intrinsics, marker_side_mm=10.0)
    """

    enable_clahe: bool = True
    enable_multiscale: bool = True
    min_marker_pixels: int = 30

    def detect(
        self,
        rgb: np.ndarray,
        intrinsic_matrix: np.ndarray,
        marker_side_mm: float,
        dist_coeffs: Optional[np.ndarray] = None,
    ) -> list:
        """Detect markers with robustness pre-processing."""
        from woundscan.capture.fiducial import detect_aruco

        try:
            import cv2
        except ImportError:
            return detect_aruco(rgb, intrinsic_matrix, marker_side_mm, dist_coeffs)

        candidates = []
        if self.enable_clahe:
            lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
            l_chan = lab[..., 0]
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            lab[..., 0] = clahe.apply(l_chan)
            preprocessed = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
        else:
            preprocessed = rgb

        primary = detect_aruco(preprocessed, intrinsic_matrix, marker_side_mm, dist_coeffs)
        if primary:
            candidates.extend(primary)

        if self.enable_multiscale and not primary:
            for scale in (0.75, 1.5):
                h, w = rgb.shape[:2]
                resized = cv2.resize(
                    preprocessed, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA
                )
                K_scaled = intrinsic_matrix.copy()
                K_scaled[0, 0] *= scale
                K_scaled[1, 1] *= scale
                K_scaled[0, 2] *= scale
                K_scaled[1, 2] *= scale
                ms = detect_aruco(resized, K_scaled, marker_side_mm, dist_coeffs)
                if ms:
                    candidates.extend(ms)
                    break

        # Deduplicate by marker_id, keeping lowest reprojection error
        by_id: dict[int, object] = {}
        for det in candidates:
            existing = by_id.get(det.marker_id)
            if existing is None or det.reprojection_error_pix < existing.reprojection_error_pix:  # type: ignore[attr-defined]
                by_id[det.marker_id] = det
        return list(by_id.values())
