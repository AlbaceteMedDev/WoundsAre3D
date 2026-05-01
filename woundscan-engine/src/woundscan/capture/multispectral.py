"""Multispectral / IR capture from the Face ID sensor on iPhone Pro models.

The TrueDepth camera projects an IR pattern visible in the front camera's
IR channel; on iPhone Pro models the rear camera array also has IR
sensitivity through the LiDAR aperture. The iOS app exposes a near-IR
channel which we use as a tissue-perfusion proxy.

This module receives a captured IR image and a wavelength tag; it does
NOT perform classification or perfusion estimation (deferred until we
have validation data).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class MultispectralCapture:
    """A multispectral capture: visible RGB plus one or more IR channels.

    Attributes
    ----------
    rgb : (H, W, 3) uint8
        Visible color.
    nir_channels : dict[str, np.ndarray]
        Mapping of wavelength label (e.g. "850nm") to (H, W) uint8 array.
    """

    rgb: np.ndarray
    nir_channels: dict[str, np.ndarray]
