"""Tests for quality components and confidence map."""
import numpy as np
import pytest

from woundscan.quality.confidence import (
    DEFAULT_WEIGHTS,
    ConfidenceWeights,
    QualityComponents,
    compute_confidence_map,
)
from woundscan.quality.edge_proximity import compute_edge_distance
from woundscan.quality.frame_consistency import compute_frame_consistency
from woundscan.quality.lighting import compute_lighting_uniformity
from woundscan.quality.motion import CameraPose, compute_motion_artifact
from woundscan.quality.specularity import compute_specularity
from woundscan.quality.texture import compute_texture_contrast


class TestSpecularity:
    def test_white_pixels_are_specular(self):
        rgb = np.full((10, 10, 3), 255, dtype=np.uint8)
        score = compute_specularity(rgb)
        assert (score > 0.9).all()

    def test_red_pixels_not_specular(self):
        rgb = np.zeros((10, 10, 3), dtype=np.uint8)
        rgb[..., 0] = 200
        score = compute_specularity(rgb)
        assert (score < 0.1).all()


class TestTexture:
    def test_uniform_image_low_texture(self):
        rgb = np.full((50, 50, 3), 128, dtype=np.uint8)
        t = compute_texture_contrast(rgb)
        assert t.mean() < 0.5

    def test_noise_image_high_texture(self):
        rgb = (np.random.default_rng(0).random((50, 50, 3)) * 255).astype(np.uint8)
        t = compute_texture_contrast(rgb)
        assert t.mean() > 0.3


class TestLighting:
    def test_uniform_lighting_high_score(self):
        rgb = np.full((50, 50, 3), 128, dtype=np.uint8)
        l = compute_lighting_uniformity(rgb)
        assert l.mean() > 0.95


class TestMotion:
    def test_no_motion_zero_artifact(self):
        poses = [
            CameraPose((0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0), 0.0),
            CameraPose((0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0), 0.5),
        ]
        m = compute_motion_artifact(poses, (10, 10))
        assert m.max() < 0.01

    def test_translation_increases_motion(self):
        poses = [
            CameraPose((0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0), 0.0),
            CameraPose((0.05, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0), 0.1),  # 50mm in 0.1s
        ]
        m = compute_motion_artifact(poses, (10, 10))
        assert m.max() > 0.5


class TestEdgeDistance:
    def test_center_pixel_high_score(self):
        mask = np.zeros((50, 50), dtype=bool)
        mask[10:40, 10:40] = True
        s = compute_edge_distance(mask, dx_cm=0.1, dy_cm=0.1, saturation_distance_mm=5.0)
        assert s[25, 25] > 0.9
        assert s[10, 10] < 0.5  # near edge


class TestFrameConsistency:
    def test_identical_frames_score_one(self):
        stack = np.zeros((10, 20, 20), dtype=np.float32)
        stack[:] = 5.0
        s = compute_frame_consistency(stack)
        assert (s > 0.99).all()

    def test_noisy_frames_lower_score(self):
        rng = np.random.default_rng(0)
        stack = rng.normal(loc=5.0, scale=0.2, size=(10, 20, 20)).astype(np.float32)
        s = compute_frame_consistency(stack, saturation_std_mm=0.5)
        assert s.mean() < 0.5


class TestConfidenceMap:
    def test_weights_must_sum_to_one(self):
        with pytest.raises(ValueError):
            ConfidenceWeights(specularity=0.5, texture=0.5, lighting=0.5)

    def test_default_weights_valid(self):
        # Should not raise
        ConfidenceWeights()

    def test_perfect_inputs_high_confidence(self):
        shape = (20, 20)
        comp = QualityComponents(
            specularity=np.zeros(shape),
            texture=np.ones(shape),
            lighting=np.ones(shape),
            motion=np.zeros(shape),
            edge_distance=np.ones(shape),
            frame_consistency=np.ones(shape),
            boundary_confidence=np.ones(shape),
        )
        c = compute_confidence_map(comp, DEFAULT_WEIGHTS)
        assert (c > 0.99).all()

    def test_terrible_inputs_low_confidence(self):
        shape = (20, 20)
        comp = QualityComponents(
            specularity=np.ones(shape),
            texture=np.zeros(shape),
            lighting=np.zeros(shape),
            motion=np.ones(shape),
            edge_distance=np.zeros(shape),
            frame_consistency=np.zeros(shape),
            boundary_confidence=np.zeros(shape),
        )
        c = compute_confidence_map(comp, DEFAULT_WEIGHTS)
        assert (c < 0.01).all()
