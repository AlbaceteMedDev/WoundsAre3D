"""FastAPI app factory and entry point."""
from __future__ import annotations

import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from woundscan import ENGINE_VERSION
from woundscan.api.routes import admin, auth, health, measurements, phantom, uploads, wounds
from woundscan.monitoring.error_reporting import init_error_reporting
from woundscan.monitoring.metrics import METRIC_REQUEST_DURATION_S, init_metrics
from woundscan.monitoring.tracing import init_tracing


def create_app() -> FastAPI:
    init_error_reporting()
    init_metrics()
    init_tracing()

    app = FastAPI(
        title="WoundScan Engine",
        version=ENGINE_VERSION,
        docs_url="/docs",
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start
        try:
            METRIC_REQUEST_DURATION_S.labels(
                method=request.method,
                route=request.url.path,
                status=str(response.status_code),
            ).observe(duration)
        except Exception:
            pass
        return response

    @app.get("/metrics")
    def metrics() -> Response:
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(uploads.router)
    app.include_router(wounds.router)
    app.include_router(measurements.router)
    app.include_router(phantom.router)
    app.include_router(admin.router)

    return app


app = create_app()


def run() -> None:
    """Entry point for the `woundscan-api` console script."""
    import uvicorn

    uvicorn.run("woundscan.api.main:app", host="0.0.0.0", port=8000, log_level="info")
