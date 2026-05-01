"""RGB photo ingestion for the wound capture session."""
from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Union

import numpy as np

from woundscan.capture.depth_map import CameraIntrinsics


@dataclass(frozen=True)
class PhotoFrame:
    """A single RGB photo with intrinsics and metadata."""

    rgb: np.ndarray  # (H, W, 3) uint8
    intrinsics: CameraIntrinsics
    timestamp_s: float
    iso: int
    shutter_speed_s: float
    aperture: float
    focal_length_mm: float

    def __post_init__(self) -> None:
        if self.rgb.ndim != 3 or self.rgb.shape[2] != 3:
            raise ValueError(f"rgb must be (H, W, 3), got {self.rgb.shape}")
        if self.rgb.dtype != np.uint8:
            raise ValueError(f"rgb must be uint8, got {self.rgb.dtype}")


def load_photo(
    image: Union[bytes, np.ndarray, str],
    intrinsics: CameraIntrinsics,
    timestamp_s: float,
    iso: int = 100,
    shutter_speed_s: float = 1.0 / 60.0,
    aperture: float = 1.8,
    focal_length_mm: float = 5.96,  # iPhone 14 Pro main camera nominal
) -> PhotoFrame:
    """Load a photo from bytes, file path, or numpy array."""
    if isinstance(image, (bytes, bytearray)):
        from PIL import Image

        img = Image.open(io.BytesIO(image)).convert("RGB")
        rgb = np.array(img, dtype=np.uint8)
    elif isinstance(image, str):
        from PIL import Image

        img = Image.open(image).convert("RGB")
        rgb = np.array(img, dtype=np.uint8)
    elif isinstance(image, np.ndarray):
        if image.dtype == np.uint8:
            rgb = image
        else:
            rgb = (np.clip(image, 0.0, 1.0) * 255).astype(np.uint8)
    else:
        raise TypeError(f"Unsupported image type: {type(image)}")

    return PhotoFrame(
        rgb=rgb,
        intrinsics=intrinsics,
        timestamp_s=timestamp_s,
        iso=iso,
        shutter_speed_s=shutter_speed_s,
        aperture=aperture,
        focal_length_mm=focal_length_mm,
    )
