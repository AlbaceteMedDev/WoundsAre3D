"""End-to-end pipeline tests.

Builds a mock CreateMeasurementRequest and runs the full pipeline,
asserting that the expected outputs are produced and within reasonable
ranges. Uses the synthetic-camera-anchors path; binary upload is not
exercised here.
"""

from __future__ import annotations

from datetime import UTC, datetime, timezone
from uuid import uuid4

import numpy as np
import pytest

from woundscan.api.models.measurement import (
    CameraIntrinsicsInput,
    CapturePoseInput,
    CreateMeasurementRequest,
    FiducialDetectionInput,
    ProbeMeasurementInput,
    UnderminingInput,
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
    undermining_mm: float | None = None,
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
        captured_at=datetime.now(UTC),
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
        undermining=[
            UnderminingInput(clock_position_hours=float(k or 12), extent_mm=undermining_mm)
            for k in range(12)
        ]
        if undermining_mm is not None
        else [],
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


class TestPipelineUndermining:
    """Undermining travels from clinician probe readings to the response."""

    def test_absent_by_default(self):
        resp = run_measurement_pipeline(
            _make_request(), PipelineDependencies(product_db=default_product_db())
        )
        u = resp.undermining
        assert u.measured is False
        assert u.n_measurements == 0
        assert u.undermined_area_cm2 == 0.0
        assert u.undermined_volume_cm3 == 0.0
        assert u.visible_area_cm2 > 0.0
        assert u.total_area_with_undermining_cm2 == pytest.approx(u.visible_area_cm2)

    def test_uniform_extent_matches_the_annulus(self):
        """Wound edge r = 20 mm, uniform 8 mm undermining -> pi(28^2 - 20^2) = 1206.37 mm^2."""
        resp = run_measurement_pipeline(
            _make_request(undermining_mm=8.0),
            PipelineDependencies(product_db=default_product_db()),
        )
        u = resp.undermining
        truth_cm2 = float(np.pi * (28.0**2 - 20.0**2)) / 100.0
        assert u.measured is True
        assert u.n_measurements == 12
        assert u.source == "clinician probe"
        # the 32-gon boundary inscribes the circle, so expect a slight shortfall
        assert u.undermined_area_cm2 == pytest.approx(truth_cm2, rel=0.03)
        assert u.total_area_with_undermining_cm2 == pytest.approx(
            u.visible_area_cm2 + u.undermined_area_cm2
        )
        assert u.undermined_area_ci_95_low_cm2 < u.undermined_area_cm2 < u.undermined_area_ci_95_high_cm2
        assert u.max_extent_mm == pytest.approx(8.0)
        assert len(u.involved_clock_positions) == 12
        assert u.pocket_height_mm > 0.0
        assert u.pocket_height_basis
        assert u.undermined_volume_cm3 == pytest.approx(
            u.undermined_area_cm2 * u.pocket_height_mm / 10.0, rel=1e-6
        )
