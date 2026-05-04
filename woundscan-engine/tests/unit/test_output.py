"""Tests for output: PDF, CSV, FHIR, provenance."""

import json
from datetime import datetime, timezone

import numpy as np
import pytest

from woundscan.output.csv_export import COLUMNS, write_measurement_csv
from woundscan.output.fhir_export import build_fhir_observation_bundle
from woundscan.output.provenance import (
    InputHash,
    build_provenance_record,
    hash_array,
)


class TestProvenance:
    def test_hash_array_deterministic(self):
        a = np.arange(10).reshape(2, 5)
        h1 = hash_array(a)
        h2 = hash_array(a.copy())
        assert h1.sha256 == h2.sha256

    def test_different_array_different_hash(self):
        a = np.arange(10)
        b = np.arange(10) + 1
        assert hash_array(a).sha256 != hash_array(b).sha256

    def test_build_provenance(self):
        rec = build_provenance_record(
            measurement_id="m1",
            captured_at=datetime.now(timezone.utc),
            processed_at=datetime.now(timezone.utc),
            processing_duration_ms=123.4,
            engine_version="1.0.0",
            git_sha="abc",
            confidence_weights_version="v1",
            force_correction_version="v1",
            boundary_model_version="v1",
            boundary_model_sha256="x",
            tissue_model_version="v1",
            tissue_model_sha256="y",
            probe_model_version="v1",
            probe_model_sha256="z",
            input_hashes=[InputHash(name="rgb", sha256="a", bytes_size=100)],
            intermediate_hashes=[],
            config_dict={"a": 1},
        )
        # JSON should round-trip
        data = json.loads(rec.to_json())
        assert data["engine_version"] == "1.0.0"


class TestCSVExport:
    def test_writes_columns(self):
        rows = [{"measurement_id": "m1", "volume_cm3": 1.5, "quality_grade": "A"}]
        out = write_measurement_csv(rows)
        assert "measurement_id" in out
        assert "m1" in out
        # Headers include all standard columns
        for col in COLUMNS:
            assert col in out


class TestFHIR:
    def test_bundle_has_three_observations(self):
        bundle = build_fhir_observation_bundle(
            patient_token="p1",
            measurement_id="m1",
            captured_at=datetime.now(timezone.utc),
            volume_cm3=1.0,
            volume_ci_low=0.9,
            volume_ci_high=1.1,
            surface_area_cm2=2.0,
            surface_area_ci_low=1.8,
            surface_area_ci_high=2.2,
            max_depth_cm=0.5,
        )
        assert bundle["resourceType"] == "Bundle"
        assert len(bundle["entry"]) == 3
