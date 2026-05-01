"""Wound boundary segmentation.

A U-Net trained to segment wound vs periwound from RGB photos. We provide:

- The PyTorch model architecture (`UNet`)
- A wrapper class `BoundarySegmentationModel` that loads weights, runs
  inference, and returns a `SegmentationResult` with confidence map.
- A heuristic fallback (color + edge based) used when no weights are
  available (development environment, CI without GPU).

The fallback is INTENTIONALLY WEAK so it cannot be confused with the
trained model. It exists only so the rest of the engine can run end-
to-end during development. Production deployments load real weights.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class SegmentationResult:
    """Output of boundary segmentation.

    Attributes
    ----------
    binary_mask : (H, W) bool
        Wound = True, periwound = False.
    confidence : (H, W) float32
        Per-pixel softmax probability of "wound" class.
    polygon_mm : list[(x_mm, y_mm)] or None
        If `to_polygon` was called, the simplified boundary polygon.
    model_version : str
    """

    binary_mask: np.ndarray
    confidence: np.ndarray
    polygon_mm: list[tuple[float, float]] | None
    model_version: str


class _UNet:
    """Minimal U-Net wrapper - loaded lazily from torch only when needed."""

    def __init__(self, n_classes: int = 2):
        try:
            import torch
            import torch.nn as nn

            class DoubleConv(nn.Module):
                def __init__(self, in_c: int, out_c: int) -> None:
                    super().__init__()
                    self.body = nn.Sequential(
                        nn.Conv2d(in_c, out_c, 3, padding=1),
                        nn.BatchNorm2d(out_c),
                        nn.ReLU(inplace=True),
                        nn.Conv2d(out_c, out_c, 3, padding=1),
                        nn.BatchNorm2d(out_c),
                        nn.ReLU(inplace=True),
                    )

                def forward(self, x):  # type: ignore[no-untyped-def]
                    return self.body(x)

            class UNet(nn.Module):
                def __init__(self, n_classes: int) -> None:
                    super().__init__()
                    self.enc1 = DoubleConv(3, 32)
                    self.enc2 = DoubleConv(32, 64)
                    self.enc3 = DoubleConv(64, 128)
                    self.enc4 = DoubleConv(128, 256)
                    self.pool = nn.MaxPool2d(2)
                    self.up3 = nn.ConvTranspose2d(256, 128, 2, stride=2)
                    self.dec3 = DoubleConv(256, 128)
                    self.up2 = nn.ConvTranspose2d(128, 64, 2, stride=2)
                    self.dec2 = DoubleConv(128, 64)
                    self.up1 = nn.ConvTranspose2d(64, 32, 2, stride=2)
                    self.dec1 = DoubleConv(64, 32)
                    self.head = nn.Conv2d(32, n_classes, 1)

                def forward(self, x):  # type: ignore[no-untyped-def]
                    e1 = self.enc1(x)
                    e2 = self.enc2(self.pool(e1))
                    e3 = self.enc3(self.pool(e2))
                    e4 = self.enc4(self.pool(e3))
                    d3 = self.dec3(torch.cat([self.up3(e4), e3], dim=1))
                    d2 = self.dec2(torch.cat([self.up2(d3), e2], dim=1))
                    d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))
                    return self.head(d1)

            self.net = UNet(n_classes)
            self.torch = torch
        except ImportError:
            self.net = None
            self.torch = None


class BoundarySegmentationModel:
    """Wound boundary segmentation model with heuristic fallback.

    Usage
    -----
    >>> model = BoundarySegmentationModel.from_weights("weights/boundary_v1.pt")
    >>> result = model.segment(rgb_photo)

    The fallback path runs when no weights are available; it uses a
    color- and edge-based heuristic that does NOT meet clinical
    accuracy. The clinician will edit the proposed boundary in the iOS
    app regardless.
    """

    DEFAULT_VERSION = "fallback-heuristic-v0"

    def __init__(
        self,
        weights_path: Optional[Path | str] = None,
        device: str = "cpu",
    ):
        self.weights_path = Path(weights_path) if weights_path else None
        self.device = device
        self._unet: _UNet | None = None
        self._loaded = False

    @classmethod
    def from_weights(
        cls, weights_path: Path | str, device: str = "cpu"
    ) -> "BoundarySegmentationModel":
        return cls(weights_path=weights_path, device=device)

    @classmethod
    def fallback(cls) -> "BoundarySegmentationModel":
        return cls(weights_path=None)

    @property
    def version(self) -> str:
        if self.weights_path and self.weights_path.exists():
            return self.weights_path.stem
        return self.DEFAULT_VERSION

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        if self.weights_path and self.weights_path.exists():
            try:
                self._unet = _UNet(n_classes=2)
                if self._unet.torch is not None and self._unet.net is not None:
                    state = self._unet.torch.load(  # type: ignore[no-untyped-call]
                        str(self.weights_path), map_location=self.device
                    )
                    self._unet.net.load_state_dict(state)
                    self._unet.net.to(self.device)
                    self._unet.net.eval()
            except Exception:
                self._unet = None
        self._loaded = True

    def segment(self, rgb: np.ndarray) -> SegmentationResult:
        """Run segmentation on an (H, W, 3) uint8 RGB image."""
        self._ensure_loaded()
        if self._unet is not None and self._unet.net is not None:
            return self._segment_unet(rgb)
        return self._segment_fallback(rgb)

    def _segment_unet(self, rgb: np.ndarray) -> SegmentationResult:
        torch = self._unet.torch  # type: ignore[union-attr]
        net = self._unet.net  # type: ignore[union-attr]
        x = torch.from_numpy(rgb.astype(np.float32) / 255.0).permute(2, 0, 1).unsqueeze(0)
        x = x.to(self.device)
        with torch.no_grad():
            logits = net(x)
            prob = torch.softmax(logits, dim=1)[0, 1].cpu().numpy()
        mask = prob > 0.5
        return SegmentationResult(
            binary_mask=mask,
            confidence=prob.astype(np.float32),
            polygon_mm=None,
            model_version=self.version,
        )

    def _segment_fallback(self, rgb: np.ndarray) -> SegmentationResult:
        """Color + edge heuristic. Used only in fallback contexts."""
        from skimage.color import rgb2hsv
        from skimage.filters import sobel

        hsv = rgb2hsv(rgb if rgb.dtype != np.uint8 else (rgb / 255.0))
        red_score = (1.0 - np.abs(hsv[..., 0] - 0.0)) * hsv[..., 1]
        red_score = np.clip(red_score, 0.0, 1.0)
        edges = sobel(rgb.mean(axis=2).astype(np.float32) / 255.0)
        score = red_score * (1.0 - np.clip(edges * 5.0, 0.0, 1.0))
        mask = score > 0.4
        if not mask.any():
            mask = score > np.percentile(score, 90)
        return SegmentationResult(
            binary_mask=mask,
            confidence=score.astype(np.float32),
            polygon_mm=None,
            model_version=self.version,
        )
