"""Health and version endpoints (unauthenticated)."""

from __future__ import annotations

from fastapi import APIRouter

from woundscan import ENGINE_VERSION

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
def readyz() -> dict[str, str]:
    return {"status": "ready"}


@router.get("/version")
def version() -> dict[str, str]:
    return {"engine_version": ENGINE_VERSION}
