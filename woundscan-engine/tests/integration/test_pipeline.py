"""End-to-end pipeline tests.

Builds a mock CreateMeasurementRequest and runs the full pipeline,
asserting that the expected outputs are produced and within reasonable
ranges. Uses the synthetic-camera-anchors path; binary upload is not
exercised here.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import numpy as np
import pytest

from woundscan.api.models.measurement import (
    CameraIntrinsicsInput,
    CapturePoseInput,
    CreateMeasurementRequest,
    FiducialDetectionInput,
    ProbeMeasurementInput,
    WoundBoundaryInput,
)
from woundscan.api.pipeline import PipelineDependencies, run_measurement_pipeline
from woundscan.graft.product_db import default_product_db


def _circle_polygon(r_mm: float, n: int = 32) -> list[list[float]]:
    return [
        [r_mm * float(np.cos(2 * np.pi * i / n)), r_mm * float(np.sin(2 * np.pi * i / n))]
        for i in range(n)
    ]


def _make_request(
    n_anchors: int = 9,
    radius_mm: float = 20.0,
    depth_mm: float = 10.0,
) -> CreateMeasurementRequest:
    intr = CameraIntrinsicsInput(fx=500.0, fy=500.0, cx=320.0, cy=240.0, width=640, height=480)
    pose = CapturePoseInput(
        position_m=[0.0, 0.0, 0.3],
        rotation_quat=[0.0, 0.0, 0.0, 1.0],
        timestamp_s=0.0,
    )
    boundary = WoundBoundaryInput(vertices_mm=_circle_polygon(radius_mm))
    rng = np.random.default_rng(0)
    probes: list[ProbeMeasurementInput] = []
    for i in range(n_anchors):
        theta = 2 * np.pi * i / n_anchors
        r = radius_mm * 0.5
        probes.append(
            ProbeMeasurementInput(
                x_mm=float(r * np.cos(theta)),
                y_mm=float(r * np.sin(theta)),
                depth_mm=depth_mm + float(rng.normal(scale=0.5)),
                force_category="medium",
                probe_type="cotton_tip",
                auto_detected=False,
                notes="",
            )
        )
    return CreateMeasurementRequest(
        wound_id=uuid4(),
        captured_at=datetime.now(timezone.utc),
        intrinsics=intr,
        rgb_s3_key="key/rgb",
        depth_burst_s3_keys=["key/depth-0", "key/depth-1"],
        poses=[pose],
        fiducials=[
            FiducialDetectionInput(
                marker_id=0,
                corners_pix=[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]],
                rvec=[0.0, 0.0, 0.0],
                tvec=[0.0, 0.0, 0.3],
                reprojection_error_pix=0.4,
            )
            for _ in range(4)
        ],
        fiducial_marker_side_mm=10.0,
        fiducial_separation_mm=50.0,
        boundary=boundary,
        probe_measurements=probes,
        overlap_delta_cm=0.5,
        selected_product_ids=[],
    )


class TestPipeline:
    def test_pipeline_produces_response(self):
        req = _make_request()
        deps = PipelineDependencies(product_db=default_product_db())
        resp = run_measurement_pipeline(req, deps)
        assert resp.measurement_id is not None
        assert resp.volume.mean > 0
        assert resp.surface_area.mean > 0
        assert resp.quality.grade in ("A", "B", "C", "F")
        assert resp.processing_duration_ms > 0
        assert resp.provenance["engine_version"]

    def test_pipeline_volume_in_expected_range(self):
        req = _make_request(radius_mm=20.0, depth_mm=10.0)
        deps = PipelineDependencies(product_db=default_product_db())
        resp = run_measurement_pipeline(req, deps)
        # Bowl with r=2cm, h~1cm should have V on the order of 1-3 cm^3
        # depending on shape. GP fusion produces a smooth surface.
        assert 0.5 < resp.volume.mean < 30.0

    def test_pipeline_handles_no_probe(self):
        req = _make_request(n_anchors=0)
        deps = PipelineDependencies(product_db=default_product_db())
        resp = run_measurement_pipeline(req, deps)
        assert resp.quality.grade == "F"
        assert resp.volume.mean == 0.0

    def test_pipeline_provenance_has_all_fields(self):
        req = _make_request()
        deps = PipelineDependencies(product_db=default_product_db())
        resp = run_measurement_pipeline(req, deps)
        prov = resp.provenance
        for key in (
            "engine_version",
            "captured_at",
            "processed_at",
            "confidence_weights_version",
            "force_correction_version",
            "input_hashes",
            "intermediate_hashes",
        ):
            assert key in prov
