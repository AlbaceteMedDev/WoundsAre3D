"""Tests for the ML wrapper modules: tissue_classification, probe_detection,
fiducial_robust.

These exercise the heuristic / fallback paths in-process (no torch
required). The boundary_segmentation U-Net path is already covered by
the subprocess-isolated `test_boundary_segmentation.py` suite.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from woundscan.ml.fiducial_robust import RobustFiducialDetector
from woundscan.ml.probe_detection import ProbeDetection, ProbeDetectionModel
from woundscan.ml.tissue_classification import (
    TissueClass,
    TissueClassificationModel,
    TissueClassificationResult,
)


# ---------------------------------------------------------------------------
# probe_detection — small, deterministic
# ---------------------------------------------------------------------------


class TestProbeDetectionModel:
    def test_fallback_returns_empty_list(self):
        model = ProbeDetectionModel.fallback()
        img = np.zeros((64, 64, 3), dtype=np.uint8)
        assert model.detect(img) == []

    def test_fallback_version_string(self):
        model = ProbeDetectionModel.fallback()
        assert model.version == ProbeDetectionModel.DEFAULT_VERSION

    def test_missing_weights_path_falls_back(self, tmp_path: Path):
        model = ProbeDetectionModel.from_weights(tmp_path / "nope.pt")
        assert model.detect(np.zeros((64, 64, 3), dtype=np.uint8)) == []
        # The version still reports the fallback string when the file is absent.
        assert model.version == ProbeDetectionModel.DEFAULT_VERSION

    def test_present_weights_path_version_uses_stem(self, tmp_path: Path):
        ckpt = tmp_path / "probe_v3.pt"
        ckpt.write_bytes(b"stub")
        model = ProbeDetectionModel.from_weights(ckpt)
        assert model.version == "probe_v3"
        # No real weights = empty detections (production path is a stub).
        assert model.detect(np.zeros((64, 64, 3), dtype=np.uint8)) == []

    def test_dataclass_is_frozen(self):
        d = ProbeDetection(bbox_xyxy=(0, 0, 10, 10), tip_pix=(5, 5), confidence=0.9, model_version="x")
        with pytest.raises(Exception):
            d.confidence = 0.5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# tissue_classification — heuristic fallback
# ---------------------------------------------------------------------------


def _granulation_image(size: int = 32) -> np.ndarray:
    """Image dominated by red pixels (granulation tissue)."""
    img = np.zeros((size, size, 3), dtype=np.uint8)
    img[..., 0] = 200  # red
    img[..., 1] = 30
    img[..., 2] = 30
    return img


def _eschar_image(size: int = 32) -> np.ndarray:
    """Dark, near-black image — should classify as eschar."""
    return np.full((size, size, 3), 12, dtype=np.uint8)


class TestTissueClassificationModel:
    def test_fallback_classifies_granulation(self):
        model = TissueClassificationModel.fallback()
        img = _granulation_image()
        result = model.classify(img)
        assert isinstance(result, TissueClassificationResult)
        assert result.class_map.shape == (32, 32)
        assert result.probabilities.shape == (32, 32, len(TissueClass))
        # Probabilities sum to ~1 per pixel.
        sums = result.probabilities.sum(axis=-1)
        assert np.allclose(sums, 1.0, atol=1e-4)
        # Composition has all classes (mask=None branch).
        assert set(result.composition.keys()) == set(TissueClass)

    def test_fallback_classifies_eschar(self):
        model = TissueClassificationModel.fallback()
        img = _eschar_image()
        result = model.classify(img)
        # The dominant class in a very dark image should be eschar.
        eschar_frac = result.composition[TissueClass.ESCHAR]
        assert eschar_frac > 0.4

    def test_composition_with_mask_excludes_periwound(self):
        model = TissueClassificationModel.fallback()
        img = _granulation_image(16)
        mask = np.zeros((16, 16), dtype=bool)
        mask[4:12, 4:12] = True
        result = model.classify(img, mask=mask)
        # When a mask is provided, periwound is dropped from composition.
        assert TissueClass.PERIWOUND not in result.composition

    def test_version_uses_weights_stem_when_present(self, tmp_path: Path):
        ckpt = tmp_path / "tissue_v2.pt"
        ckpt.write_bytes(b"stub")
        model = TissueClassificationModel.from_weights(ckpt)
        assert model.version == "tissue_v2"

    def test_version_uses_default_when_absent(self, tmp_path: Path):
        model = TissueClassificationModel(weights_path=tmp_path / "missing.pt")
        assert model.version == TissueClassificationModel.DEFAULT_VERSION

    def test_classify_accepts_float_image(self):
        model = TissueClassificationModel.fallback()
        img = np.full((16, 16, 3), 0.6, dtype=np.float32)
        result = model.classify(img)
        assert result.class_map.shape == (16, 16)


# ---------------------------------------------------------------------------
# fiducial_robust — CLAHE pre-processing + multi-scale retry
# ---------------------------------------------------------------------------


def _make_aruco_image(size: int = 480) -> np.ndarray:
    import cv2

    img = np.full((size, size, 3), 255, dtype=np.uint8)
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_5X5_50)
    marker = cv2.aruco.generateImageMarker(aruco_dict, 7, 200)
    marker_rgb = cv2.cvtColor(marker, cv2.COLOR_GRAY2RGB)
    # Place near the center.
    x0, y0 = (size - 200) // 2, (size - 200) // 2
    img[y0:y0 + 200, x0:x0 + 200] = marker_rgb
    return img


def _intrinsics() -> np.ndarray:
    return np.array(
        [[500.0, 0.0, 240.0], [0.0, 500.0, 240.0], [0.0, 0.0, 1.0]], dtype=np.float64
    )


class TestRobustFiducialDetector:
    def test_default_settings(self):
        det = RobustFiducialDetector()
        assert det.enable_clahe is True
        assert det.enable_multiscale is True
        assert det.min_marker_pixels == 30

    def test_detects_with_clahe_enabled(self):
        det = RobustFiducialDetector(enable_clahe=True)
        img = _make_aruco_image()
        results = det.detect(img, _intrinsics(), marker_side_mm=60.0)
        assert any(d.marker_id == 7 for d in results)

    def test_detects_with_clahe_disabled(self):
        det = RobustFiducialDetector(enable_clahe=False, enable_multiscale=False)
        img = _make_aruco_image()
        results = det.detect(img, _intrinsics(), marker_side_mm=60.0)
        assert any(d.marker_id == 7 for d in results)

    def test_returns_empty_on_blank_image(self):
        det = RobustFiducialDetector(enable_multiscale=False)
        blank = np.full((480, 480, 3), 255, dtype=np.uint8)
        results = det.detect(blank, _intrinsics(), marker_side_mm=60.0)
        assert results == []

    def test_dedups_by_marker_id(self):
        # Multi-scale retry can produce the same marker at different scales —
        # detector dedupes keeping the lowest reprojection error.
        det = RobustFiducialDetector(enable_multiscale=True)
        img = _make_aruco_image()
        results = det.detect(img, _intrinsics(), marker_side_mm=60.0)
        ids = [d.marker_id for d in results]
        assert len(ids) == len(set(ids))
