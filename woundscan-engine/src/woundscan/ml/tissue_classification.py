"""Tissue type classification.

Per-pixel classification of wound bed tissue into:
- granulation (red, healthy)
- slough (yellow/white, devitalized)
- eschar (black, necrotic)
- epithelial (pink, healing)
- bone/tendon (white, exposed structures)
- periwound (intact skin)

Architecture: U-Net++ or DeepLabV3, multichannel input (RGB + depth).
This module provides the wrapper. A heuristic fallback is included for
development.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Optional

import numpy as np


class TissueClass(IntEnum):
    """Tissue class labels. Order matters; used as model output channels."""

    PERIWOUND = 0
    GRANULATION = 1
    SLOUGH = 2
    ESCHAR = 3
    EPITHELIAL = 4
    BONE_TENDON = 5


@dataclass(frozen=True)
class TissueClassificationResult:
    """Output of tissue classification.

    Attributes
    ----------
    class_map : (H, W) uint8
        Per-pixel argmax class.
    probabilities : (H, W, n_classes) float32
        Softmax probabilities.
    composition : dict[TissueClass, float]
        Within-mask fraction of each class. Sums to ~1 over wound pixels.
    model_version : str
    """

    class_map: np.ndarray
    probabilities: np.ndarray
    composition: dict[TissueClass, float]
    model_version: str


class TissueClassificationModel:
    """Tissue classifier with heuristic fallback."""

    DEFAULT_VERSION = "fallback-heuristic-v0"

    def __init__(self, weights_path: Optional[Path | str] = None, device: str = "cpu"):
        self.weights_path = Path(weights_path) if weights_path else None
        self.device = device

    @classmethod
    def from_weights(cls, p: Path | str, device: str = "cpu") -> "TissueClassificationModel":
        return cls(weights_path=p, device=device)

    @classmethod
    def fallback(cls) -> "TissueClassificationModel":
        return cls(weights_path=None)

    @property
    def version(self) -> str:
        if self.weights_path and self.weights_path.exists():
            return self.weights_path.stem
        return self.DEFAULT_VERSION

    def classify(
        self,
        rgb: np.ndarray,
        depth_cm: np.ndarray | None = None,
        mask: np.ndarray | None = None,
    ) -> TissueClassificationResult:
        """Run classification. Heuristic fallback uses HSV color rules."""
        return self._classify_fallback(rgb, mask)

    def _classify_fallback(
        self, rgb: np.ndarray, mask: np.ndarray | None
    ) -> TissueClassificationResult:
        from skimage.color import rgb2hsv

        rgb_norm = rgb if rgb.dtype != np.uint8 else (rgb.astype(np.float32) / 255.0)
        hsv = rgb2hsv(rgb_norm)
        h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]

        n_classes = len(TissueClass)
        probs = np.zeros(rgb.shape[:2] + (n_classes,), dtype=np.float32)

        # Periwound: low saturation OR very pale
        periwound_score = np.clip(1.0 - s, 0.0, 1.0) * np.clip(v - 0.5, 0.0, 1.0)
        # Granulation: red, mid saturation
        granulation_score = np.where((h < 0.05) | (h > 0.95), s * v, 0.0)
        # Slough: yellow, mid-high value
        slough_score = np.where((h > 0.10) & (h < 0.20), s * v, 0.0)
        # Eschar: black, low value
        eschar_score = np.clip(1.0 - v, 0.0, 1.0) * np.clip(1.0 - s, 0.0, 1.0)
        # Epithelial: pink, mid hue
        epithelial_score = np.where((h > 0.92) | (h < 0.03), v * (1.0 - s) * 0.5, 0.0)
        # Bone/tendon: white-ish, high value
        bone_score = np.clip(v - 0.85, 0.0, 1.0) * np.clip(1.0 - s, 0.0, 1.0) * 0.5

        probs[..., TissueClass.PERIWOUND] = periwound_score
        probs[..., TissueClass.GRANULATION] = granulation_score
        probs[..., TissueClass.SLOUGH] = slough_score
        probs[..., TissueClass.ESCHAR] = eschar_score
        probs[..., TissueClass.EPITHELIAL] = epithelial_score
        probs[..., TissueClass.BONE_TENDON] = bone_score

        # Normalize to sum to 1
        total = probs.sum(axis=-1, keepdims=True) + 1e-9
        probs = probs / total

        class_map = np.argmax(probs, axis=-1).astype(np.uint8)

        composition: dict[TissueClass, float] = {}
        if mask is not None:
            n_total = max(int(np.sum(mask)), 1)
            for cls in TissueClass:
                if cls == TissueClass.PERIWOUND:
                    continue
                composition[cls] = float(np.sum((class_map == int(cls)) & mask) / n_total)
        else:
            for cls in TissueClass:
                composition[cls] = float(np.mean(class_map == int(cls)))

        return TissueClassificationResult(
            class_map=class_map,
            probabilities=probs,
            composition=composition,
            model_version=self.version,
        )
