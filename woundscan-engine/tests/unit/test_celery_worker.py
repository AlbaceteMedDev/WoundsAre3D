"""Tests for api/worker.py: Celery app construction + eager task execution.

`.apply()` runs the task synchronously without touching the broker, which
exercises the full pipeline registration / serialization path that the
production Celery worker would hit.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

import numpy as np

from woundscan.api.models.measurement import (
    CameraIntrinsicsInput,
    CapturePoseInput,
    CreateMeasurementRequest,
    FiducialDetectionInput,
    ProbeMeasurementInput,
    WoundBoundaryInput,
)


def _circle_polygon(r_mm: float, n: int = 32) -> list[list[float]]:
    return [
        [r_mm * float(np.cos(2 * np.pi * i / n)), r_mm * float(np.sin(2 * np.pi * i / n))]
        for i in range(n)
    ]


def _make_request() -> CreateMeasurementRequest:
    intr = CameraIntrinsicsInput(fx=500.0, fy=500.0, cx=320.0, cy=240.0, width=640, height=480)
    pose = CapturePoseInput(
        position_m=[0.0, 0.0, 0.3],
        rotation_quat=[0.0, 0.0, 0.0, 1.0],
        timestamp_s=0.0,
    )
    boundary = WoundBoundaryInput(vertices_mm=_circle_polygon(20.0))
    rng = np.random.default_rng(0)
    probes = [
        ProbeMeasurementInput(
            x_mm=float(10.0 * np.cos(2 * np.pi * i / 9)),
            y_mm=float(10.0 * np.sin(2 * np.pi * i / 9)),
            depth_mm=10.0 + float(rng.normal(scale=0.5)),
            force_category="medium",
            probe_type="cotton_tip",
            auto_detected=False,
            notes="",
        )
        for i in range(9)
    ]
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


class TestCeleryApp:
    def test_celery_app_constructed(self):
        from woundscan.api.worker import celery_app

        assert celery_app.main == "woundscan"
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert celery_app.conf.accept_content == ["json"]
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True

    def test_task_is_registered(self):
        from woundscan.api.worker import celery_app

        assert "woundscan.run_measurement_pipeline_async" in celery_app.tasks

    def test_eager_flag_honored(self, monkeypatch):
        monkeypatch.setenv("WS_CELERY_EAGER", "1")
        # Re-import the module-level _build_celery via a fresh call.
        from woundscan.api.worker import _build_celery

        app = _build_celery()
        assert app.conf.task_always_eager is True

    def test_eager_defaults_off(self, monkeypatch):
        monkeypatch.delenv("WS_CELERY_EAGER", raising=False)
        from woundscan.api.worker import _build_celery

        app = _build_celery()
        assert app.conf.task_always_eager is False

    def test_broker_url_from_env(self, monkeypatch):
        monkeypatch.setenv("WS_CELERY_BROKER", "redis://example:6379/9")
        from woundscan.api.worker import _build_celery

        app = _build_celery()
        assert app.conf.broker_url == "redis://example:6379/9"


class TestPipelineTaskApply:
    def test_apply_returns_valid_response_dict(self):
        # apply() runs the task synchronously without engaging the broker —
        # full serialization + pipeline path is exercised.
        from woundscan.api.worker import run_measurement_pipeline_async

        req = _make_request()
        result = run_measurement_pipeline_async.apply(args=[req.model_dump(mode="json")])
        assert result.successful()
        resp = result.get()
        assert isinstance(resp, dict)
        assert "measurement_id" in resp
        assert resp["volume"]["mean"] > 0
        assert resp["surface_area"]["mean"] > 0
        assert resp["quality"]["grade"] in ("A", "B", "C", "F")
        assert resp["provenance"]["engine_version"]


class TestRunEntrypoint:
    def test_run_invokes_worker_main(self, monkeypatch):
        # The `run()` entrypoint is invoked by the `woundscan-worker` console
        # script; we don't want to actually spawn a worker, so stub
        # `worker_main` and assert it was called with the expected argv.
        from woundscan.api import worker as worker_mod

        called: list[list[str]] = []

        def fake_worker_main(argv=None):
            called.append(argv or [])

        monkeypatch.setattr(worker_mod.celery_app, "worker_main", fake_worker_main)
        worker_mod.run()
        assert called == [["worker", "--loglevel=INFO", "--concurrency=2"]]


def test_module_imports_under_clean_env(monkeypatch):
    # Smoke: nothing at module load should fail even when no Celery env vars
    # are set — covers the os.environ.get defaults in _build_celery.
    for var in ("WS_CELERY_BROKER", "WS_CELERY_BACKEND", "WS_CELERY_EAGER"):
        monkeypatch.delenv(var, raising=False)
    import importlib

    from woundscan.api import worker as worker_mod

    importlib.reload(worker_mod)
    assert worker_mod.celery_app is not None
    # default broker
    assert worker_mod.celery_app.conf.broker_url == "redis://localhost:6379/0"
    # ensure os.environ wasn't side-effected
    assert os.environ.get("WS_CELERY_BROKER") is None
