"""Expanded FastAPI endpoint tests via TestClient.

Picks up the gaps left by `tests/integration/test_api.py`: full
measurement-pipeline POST + GET, mesh + PDF + FHIR exports, progression,
notes generation/signing/listing, graft applications + inventory,
reimbursement calculator, and the remaining admin endpoints.
"""

from __future__ import annotations

import os
from datetime import UTC, date, datetime, timedelta
from typing import Iterator
from uuid import uuid4

import numpy as np
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    os.environ["WS_JWT_SIGNING_KEY"] = "test-key"
    os.environ["WS_ALLOW_DEV_LOGIN"] = "1"
    os.environ["WS_DEV_USER"] = "dev@local"
    os.environ["WS_DEV_PASSWORD"] = "dev"
    os.environ["WS_DEV_TOTP"] = "000000"
    from woundscan.api.main import create_app

    app = create_app()
    yield TestClient(app)


@pytest.fixture(scope="module")
def token(client: TestClient) -> str:
    resp = client.post(
        "/auth/login",
        json={"email": "dev@local", "password": "dev", "totp_code": "000000"},
    )
    assert resp.status_code == 200
    return resp.json()["token"]


@pytest.fixture
def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _circle_polygon(r_mm: float, n: int = 32) -> list[list[float]]:
    return [
        [r_mm * float(np.cos(2 * np.pi * i / n)), r_mm * float(np.sin(2 * np.pi * i / n))]
        for i in range(n)
    ]


def _measurement_payload(wound_id: str | None = None) -> dict:
    """Build a CreateMeasurementRequest body the pipeline can process."""
    wound_id = wound_id or str(uuid4())
    intr = {"fx": 500.0, "fy": 500.0, "cx": 320.0, "cy": 240.0, "width": 640, "height": 480}
    pose = {
        "position_m": [0.0, 0.0, 0.3],
        "rotation_quat": [0.0, 0.0, 0.0, 1.0],
        "timestamp_s": 0.0,
    }
    rng = np.random.default_rng(0)
    probes = []
    for i in range(9):
        theta = 2 * np.pi * i / 9
        r = 10.0
        probes.append({
            "x_mm": float(r * np.cos(theta)),
            "y_mm": float(r * np.sin(theta)),
            "depth_mm": 10.0 + float(rng.normal(scale=0.5)),
            "force_category": "medium",
            "probe_type": "cotton_tip",
            "auto_detected": False,
            "notes": "",
        })
    return {
        "wound_id": wound_id,
        "captured_at": datetime.now(UTC).isoformat(),
        "intrinsics": intr,
        "rgb_s3_key": "key/rgb",
        "depth_burst_s3_keys": ["key/depth-0", "key/depth-1"],
        "poses": [pose],
        "fiducials": [
            {
                "marker_id": i,
                "corners_pix": [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]],
                "rvec": [0.0, 0.0, 0.0],
                "tvec": [0.0, 0.0, 0.3],
                "reprojection_error_pix": 0.4,
            }
            for i in range(4)
        ],
        "fiducial_marker_side_mm": 10.0,
        "fiducial_separation_mm": 50.0,
        "boundary": {"vertices_mm": _circle_polygon(20.0)},
        "probe_measurements": probes,
        "overlap_delta_cm": 0.5,
        "selected_product_ids": [],
    }


@pytest.fixture(scope="module")
def measurement(client: TestClient, token: str) -> dict:
    """Run the pipeline once and reuse the response across many tests."""
    resp = client.post(
        "/measurements",
        json=_measurement_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Measurements
# ---------------------------------------------------------------------------


class TestMeasurements:
    def test_create_returns_measurement(self, measurement: dict):
        assert "measurement_id" in measurement
        assert measurement["volume"]["mean"] > 0
        assert measurement["surface_area"]["mean"] > 0
        assert measurement["quality"]["grade"] in {"A", "B", "C", "F"}

    def test_get_by_id(self, client: TestClient, auth: dict, measurement: dict):
        mid = measurement["measurement_id"]
        resp = client.get(f"/measurements/{mid}", headers=auth)
        assert resp.status_code == 200
        assert resp.json()["measurement_id"] == mid

    def test_get_unknown_404(self, client: TestClient, auth: dict):
        resp = client.get(f"/measurements/{uuid4()}", headers=auth)
        assert resp.status_code == 404

    def test_mesh_export(self, client: TestClient, auth: dict, measurement: dict):
        mid = measurement["measurement_id"]
        resp = client.get(f"/measurements/{mid}/mesh", headers=auth)
        assert resp.status_code == 200
        body = resp.content
        assert body.startswith(b"# WoundScan reconstructed surface") or b"v " in body[:300]

    def test_pdf_export(self, client: TestClient, auth: dict, measurement: dict):
        mid = measurement["measurement_id"]
        resp = client.get(f"/measurements/{mid}/pdf", headers=auth)
        assert resp.status_code == 200
        assert resp.content[:5] == b"%PDF-"

    def test_fhir_export(self, client: TestClient, auth: dict, measurement: dict):
        mid = measurement["measurement_id"]
        resp = client.get(f"/measurements/{mid}/fhir", headers=auth)
        assert resp.status_code == 200
        bundle = resp.json()
        assert bundle["resourceType"] == "Bundle"
        assert len(bundle["entry"]) >= 1

    def test_sign_off(self, client: TestClient, auth: dict, measurement: dict):
        mid = measurement["measurement_id"]
        resp = client.post(f"/measurements/{mid}/sign-off", headers=auth)
        assert resp.status_code in (200, 204)


# ---------------------------------------------------------------------------
# Progression — depends on at least one measurement being cached for the wound.
# ---------------------------------------------------------------------------


class TestProgression:
    def test_progression_for_known_wound(
        self, client: TestClient, auth: dict, measurement: dict
    ):
        wound_id = measurement["wound_id"]
        resp = client.get(f"/wounds/{wound_id}/progression", headers=auth)
        assert resp.status_code == 200
        body = resp.json()
        assert body["wound_id"] == wound_id
        assert len(body["points"]) >= 1
        assert "trend" in body
        assert body["trend"]["is_healing"] in (True, False)

    def test_progression_empty_for_unknown_wound(self, client: TestClient, auth: dict):
        resp = client.get(f"/wounds/{uuid4()}/progression", headers=auth)
        assert resp.status_code == 200
        body = resp.json()
        assert body["points"] == []
        assert body["trend"]["first_capture_at"] is None
        assert body["trend"]["is_healing"] is False


# ---------------------------------------------------------------------------
# Grafts
# ---------------------------------------------------------------------------


def _graft_payload(wound_id: str | None = None, measurement_id: str | None = None) -> dict:
    return {
        "wound_id": wound_id or str(uuid4()),
        "measurement_id": measurement_id,
        "product_id": "ALB-001",
        "product_name": "AlbacetMatrix-A",
        "udi_di": "(01)00301234567890",
        "serial_number": "SN-12345",
        "lot_number": "LOT-XYZ",
        "expiration_date": (date.today() + timedelta(days=365)).isoformat(),
        "manufacture_date": (date.today() - timedelta(days=30)).isoformat(),
        "package_size_cm2": 16.0,
        "applied_area_cm2": 12.4,
        "waste_area_cm2": 3.6,
        "hcpcs_code": "Q4101",
        "notes": "Applied to plantar surface, secured with Mepitel.",
    }


class TestGrafts:
    def test_create_application(self, client: TestClient, auth: dict):
        resp = client.post("/grafts/applications", json=_graft_payload(), headers=auth)
        assert resp.status_code == 201, resp.text
        out = resp.json()
        assert out["product_id"] == "ALB-001"
        assert out["applied_area_cm2"] == 12.4

    def test_list_applications(self, client: TestClient, auth: dict):
        resp = client.get("/grafts/applications", headers=auth)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_application_by_id(self, client: TestClient, auth: dict):
        created = client.post(
            "/grafts/applications", json=_graft_payload(), headers=auth
        ).json()
        resp = client.get(f"/grafts/applications/{created['id']}", headers=auth)
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    def test_get_unknown_application_404(self, client: TestClient, auth: dict):
        resp = client.get(f"/grafts/applications/{uuid4()}", headers=auth)
        assert resp.status_code == 404

    def test_filter_by_wound_id(self, client: TestClient, auth: dict):
        wound_id = str(uuid4())
        client.post(
            "/grafts/applications", json=_graft_payload(wound_id=wound_id), headers=auth
        )
        resp = client.get(f"/grafts/applications?wound_id={wound_id}", headers=auth)
        assert resp.status_code == 200
        assert all(a["wound_id"] == wound_id for a in resp.json())

    def test_expired_application_rejected(self, client: TestClient, auth: dict):
        body = _graft_payload()
        body["expiration_date"] = (date.today() - timedelta(days=1)).isoformat()
        resp = client.post("/grafts/applications", json=body, headers=auth)
        assert resp.status_code == 422

    def test_inventory_expiring_endpoint(self, client: TestClient, auth: dict):
        resp = client.get("/grafts/inventory/expiring", headers=auth)
        assert resp.status_code == 200
        body = resp.json()
        # Endpoint returns a list-shaped payload of items / a summary; just
        # check we got something parseable.
        assert isinstance(body, (list, dict))


# ---------------------------------------------------------------------------
# Reimbursement calculator
# ---------------------------------------------------------------------------


class TestReimbursement:
    def test_calculate_office(self, client: TestClient, auth: dict):
        resp = client.post(
            "/reimbursement/calculate",
            json={
                "applied_area_cm2": 20.0,
                "anatomic_region": "trunk_arms_legs",
                "pos_code": "11",
                "drug_asp_per_cm2": 130.0,
                "package_size_cm2": 16.0,
            },
            headers=auth,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["primary_cpt"] == "15271"
        assert body["total_payment"] > 0
        assert "breakdown" in body

    def test_calculate_outpatient_face(self, client: TestClient, auth: dict):
        resp = client.post(
            "/reimbursement/calculate",
            json={
                "applied_area_cm2": 8.0,
                "anatomic_region": "face_scalp_digits",
                "pos_code": "22",
            },
            headers=auth,
        )
        assert resp.status_code == 200
        assert resp.json()["primary_cpt"] == "15275"


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


def _note_payload(measurement_id: str, *, wound_id: str | None = None) -> dict:
    return {
        "measurement_id": measurement_id,
        "anatomic_location": "right_foot_plantar",
        "wound_type": "DFU",
        "patient_token": "p-deidentified",
        "tissue_types": {"granulation": 0.6, "slough": 0.4},
        "drainage_amount": "moderate",
        "drainage_color": "serous",
        "odor": "none",
        "exudate_consistency": "thin",
        "wound_edges": "punched-out",
        "periwound_skin": "intact",
        "infection_signs": "none",
        "pain_score": 3,
        "grafts_applied": [],
        "reimbursement_hints": None,
        "prior_volume_cm3": 5.5,
        "prior_area_cm2": 13.0,
        "prior_max_depth_cm": 1.2,
        "days_since_prior": 7,
    }


class TestNotes:
    def test_create_and_sign_and_list(
        self, client: TestClient, auth: dict, measurement: dict
    ):
        mid = measurement["measurement_id"]
        created = client.post(
            "/notes", json=_note_payload(mid), headers=auth
        )
        assert created.status_code == 201, created.text
        note = created.json()
        assert note["body_text"]
        assert note["is_signed"] is False

        signed = client.post(f"/notes/{note['id']}/sign", headers=auth)
        assert signed.status_code == 200
        assert signed.json()["is_signed"] is True

        listed = client.get("/notes", headers=auth).json()
        assert any(n["id"] == note["id"] for n in listed)

    def test_create_with_unknown_measurement_404(self, client: TestClient, auth: dict):
        body = _note_payload(str(uuid4()))
        resp = client.post("/notes", json=body, headers=auth)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------


class TestAdminEndpoints:
    def test_audit_forbidden_for_clinician(self, client: TestClient, auth: dict):
        # /admin/audit requires Permission.READ_AUDIT_LOG which the
        # clinician role doesn't carry — exercises the _require gate.
        resp = client.get("/admin/audit", headers=auth)
        assert resp.status_code == 403

    def test_ml_metrics_forbidden_for_clinician(self, client: TestClient, auth: dict):
        resp = client.get("/admin/ml-metrics", headers=auth)
        assert resp.status_code == 403

    def test_audit_allowed_for_admin(self, client: TestClient):
        # Manually issue a JWT with admin role to cover the happy path.
        from uuid import UUID

        from woundscan.api.auth import _signing_key
        from woundscan.auth.identity import Role
        from woundscan.auth.sessions import create_session, issue_jwt

        sess = create_session(
            user_id=UUID("00000000-0000-0000-0000-000000000007"),
            role=Role.ADMIN.value,
            organization_id=UUID("00000000-0000-0000-0000-000000000010"),
        )
        admin_token = issue_jwt(sess, _signing_key())
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        resp = client.get("/admin/audit", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "entries" in body
        assert "total" in body

        resp = client.get("/admin/ml-metrics", headers=admin_headers)
        assert resp.status_code == 200
        assert "boundary_iou_mean" in resp.json()
