"""FastAPI endpoint tests using TestClient."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client() -> TestClient:
    os.environ["WS_JWT_SIGNING_KEY"] = "test-key"
    os.environ["WS_DEV_USER"] = "dev@local"
    os.environ["WS_DEV_PASSWORD"] = "dev"
    os.environ["WS_DEV_TOTP"] = "000000"
    from woundscan.api.main import create_app

    app = create_app()
    return TestClient(app)


@pytest.fixture(scope="module")
def auth_token(client: TestClient) -> str:
    resp = client.post(
        "/auth/login",
        json={"email": "dev@local", "password": "dev", "totp_code": "000000"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


class TestHealth:
    def test_healthz(self, client: TestClient) -> None:
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_version(self, client: TestClient) -> None:
        resp = client.get("/version")
        assert resp.status_code == 200
        assert "engine_version" in resp.json()


class TestAuth:
    def test_invalid_login(self, client: TestClient) -> None:
        resp = client.post(
            "/auth/login",
            json={"email": "wrong", "password": "wrong", "totp_code": "wrong"},
        )
        assert resp.status_code == 401

    def test_me_requires_token(self, client: TestClient) -> None:
        resp = client.get("/auth/me")
        assert resp.status_code == 401

    def test_me_with_token(self, client: TestClient, auth_token: str) -> None:
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {auth_token}"})
        assert resp.status_code == 200
        assert "user_id" in resp.json()


class TestUploads:
    def test_presigned(self, client: TestClient, auth_token: str) -> None:
        from uuid import uuid4

        resp = client.post(
            "/uploads/presigned",
            json={"wound_id": str(uuid4()), "artifact_type": "rgb", "file_count": 2},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["uploads"]) == 2


class TestWounds:
    def test_create_and_list(self, client: TestClient, auth_token: str) -> None:
        resp = client.post(
            "/wounds",
            json={
                "patient_token": "p1",
                "anatomic_location": "right_foot_plantar",
                "wound_type": "DFU",
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 201
        wound = resp.json()
        wound_id = wound["id"]

        listed = client.get("/wounds", headers={"Authorization": f"Bearer {auth_token}"}).json()
        assert any(w["id"] == wound_id for w in listed)


class TestPhantom:
    def test_submit_phantom(self, client: TestClient, auth_token: str) -> None:
        resp = client.post(
            "/phantom",
            json={
                "phantom_catalog_id": "P1",
                "measured_volume_cm3": 1.0,
                "measured_surface_area_cm2": 2.0,
                "true_volume_cm3": 1.0,
                "true_surface_area_cm2": 2.0,
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "recorded"


class TestAdmin:
    def test_products(self, client: TestClient, auth_token: str) -> None:
        resp = client.get("/admin/products", headers={"Authorization": f"Bearer {auth_token}"})
        assert resp.status_code == 200
        assert len(resp.json()["products"]) > 0
