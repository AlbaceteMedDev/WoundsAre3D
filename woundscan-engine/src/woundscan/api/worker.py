"""Celery worker for long-running fusion jobs.

The synchronous /measurements POST returns within the API timeout. For
larger captures (high-resolution multi-view bundle adjustment, GPyTorch
sparse GP on 100x100+ grids) the API enqueues a Celery task and returns
a job_id; the iOS app polls for status.

Production deployments use a Redis broker. The dev path uses an
in-process eager mode so jobs run synchronously without Redis.
"""

from __future__ import annotations

import os

from celery import Celery


def _build_celery() -> Celery:
    broker = os.environ.get("WS_CELERY_BROKER", "redis://localhost:6379/0")
    backend = os.environ.get("WS_CELERY_BACKEND", "redis://localhost:6379/1")
    app = Celery("woundscan", broker=broker, backend=backend)
    app.conf.task_always_eager = os.environ.get("WS_CELERY_EAGER", "0") == "1"
    app.conf.task_serializer = "json"
    app.conf.result_serializer = "json"
    app.conf.accept_content = ["json"]
    app.conf.timezone = "UTC"
    app.conf.enable_utc = True
    return app


celery_app = _build_celery()


@celery_app.task(name="woundscan.run_measurement_pipeline_async")
def run_measurement_pipeline_async(request_payload: dict) -> dict:
    """Async wrapper around the pipeline orchestrator."""
    from woundscan.api.models.measurement import CreateMeasurementRequest
    from woundscan.api.pipeline import PipelineDependencies, run_measurement_pipeline
    from woundscan.graft.product_db import default_product_db

    req = CreateMeasurementRequest.model_validate(request_payload)
    deps = PipelineDependencies(product_db=default_product_db())
    response = run_measurement_pipeline(req, deps)
    return response.model_dump(mode="json")


def run() -> None:
    """Entry point for the `woundscan-worker` console script."""
    celery_app.worker_main(argv=["worker", "--loglevel=INFO", "--concurrency=2"])
