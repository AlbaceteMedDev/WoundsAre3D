"""Capture: ingestion of multimodal sensor data from iOS app."""
from __future__ import annotations

from woundscan.capture.depth_map import DepthFrame, load_depth_frame
from woundscan.capture.fiducial import FiducialDetection, detect_aruco
from woundscan.capture.multiframe import temporal_average_depth
from woundscan.capture.multispectral import MultispectralCapture
from woundscan.capture.photo import PhotoFrame, load_photo
from woundscan.capture.point_cloud import PointCloud, depth_to_point_cloud
from woundscan.capture.polarization import PolarizedCapture
from woundscan.capture.probe import ForceCategory, ProbeMeasurement, ProbeType

__all__ = [
    "DepthFrame",
    "FiducialDetection",
    "ForceCategory",
    "MultispectralCapture",
    "PhotoFrame",
    "PointCloud",
    "PolarizedCapture",
    "ProbeMeasurement",
    "ProbeType",
    "depth_to_point_cloud",
    "detect_aruco",
    "load_depth_frame",
    "load_photo",
    "temporal_average_depth",
]
