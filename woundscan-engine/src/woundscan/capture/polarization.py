"""Cross-polarized capture support.

Optional accessory: a polarizer attachment over the iPhone flash and a
matched analyzer over the camera. Cross-polarized illumination removes
specular reflections and reveals subsurface tissue color, which improves
both LiDAR confidence (no specular dropout) and tissue-class accuracy.

The iOS app captures a paired (cross_polarized, parallel_polarized) image
when the polarizer is detected. We diff and recombine to extract diffuse
(skin/tissue interior) and specular (surface gloss) channels.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PolarizedCapture:
    """A paired polarization capture.

    Attributes
    ----------
    cross_polarized : (H, W, 3) uint8
        Camera and source polarizers crossed; contains only diffuse light.
    parallel_polarized : (H, W, 3) uint8
        Camera and source polarizers aligned; contains diffuse + specular.
    """

    cross_polarized: np.ndarray
    parallel_polarized: np.ndarray


def extract_diffuse_specular(
    capture: PolarizedCapture,
) -> tuple[np.ndarray, np.ndarray]:
    """Decompose into diffuse and specular components.

    Standard polarization-difference imaging:
        diffuse  ≈ cross_polarized
        specular ≈ parallel_polarized - cross_polarized

    Returns
    -------
    (diffuse_rgb, specular_rgb)
        Both (H, W, 3) uint8.
    """
    if capture.cross_polarized.shape != capture.parallel_polarized.shape:
        raise ValueError("Polarized images must have matching shape")
    diffuse = capture.cross_polarized
    specular = np.clip(
        capture.parallel_polarized.astype(np.int16) - capture.cross_polarized.astype(np.int16),
        0,
        255,
    ).astype(np.uint8)
    return diffuse, specular
