"""Provenance: full audit chain on every measurement.

Every output carries:
- Engine version and git SHA
- ML model versions and weights hashes
- Confidence weights version
- Force correction table version
- SHA-256 of every input artifact (depth frames, RGB, probe entries)
- SHA-256 of intermediate artifacts (fused depth, GP posterior std)
- Timestamps (capture_at, processed_at)
- Processing duration

This is the regulatory audit chain that allows any output to be
reconstructed and reviewed years later. Stored alongside the result and
in the audit log.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

import numpy as np


@dataclass(frozen=True)
class InputHash:
    """SHA-256 of a named input artifact."""

    name: str
    sha256: str
    bytes_size: int


@dataclass(frozen=True)
class ProvenanceRecord:
    """Complete provenance record for a measurement.

    All values are content-hashed where possible. The full record is
    serialized to JSON in the PDF report and stored as a column in the
    measurement table.
    """

    measurement_id: str
    captured_at: str
    processed_at: str
    processing_duration_ms: float
    engine_version: str
    git_sha: str
    confidence_weights_version: str
    force_correction_version: str
    boundary_model_version: str
    boundary_model_sha256: str
    tissue_model_version: str
    tissue_model_sha256: str
    probe_model_version: str
    probe_model_sha256: str
    input_hashes: list[InputHash]
    intermediate_hashes: list[InputHash]
    config_hash: str
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_json(self) -> str:
        d = asdict(self)
        return json.dumps(d, sort_keys=True, separators=(",", ":"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_array(arr: np.ndarray) -> InputHash:
    """SHA-256 of a numpy array's bytes (after C-contiguous + dtype tag)."""
    if not arr.flags["C_CONTIGUOUS"]:
        arr = np.ascontiguousarray(arr)
    payload = bytes(str(arr.dtype).encode()) + bytes(str(arr.shape).encode()) + arr.tobytes()
    return InputHash(name="array", sha256=hash_bytes(payload), bytes_size=arr.nbytes)


def build_provenance_record(
    measurement_id: str,
    captured_at: datetime,
    processed_at: datetime,
    processing_duration_ms: float,
    engine_version: str,
    git_sha: str,
    confidence_weights_version: str,
    force_correction_version: str,
    boundary_model_version: str,
    boundary_model_sha256: str,
    tissue_model_version: str,
    tissue_model_sha256: str,
    probe_model_version: str,
    probe_model_sha256: str,
    input_hashes: list[InputHash],
    intermediate_hashes: list[InputHash],
    config_dict: dict[str, Any],
    notes: tuple[str, ...] = (),
) -> ProvenanceRecord:
    """Compute and bundle all provenance fields into a record."""
    config_payload = json.dumps(config_dict, sort_keys=True).encode()
    return ProvenanceRecord(
        measurement_id=measurement_id,
        captured_at=captured_at.isoformat(),
        processed_at=processed_at.isoformat(),
        processing_duration_ms=processing_duration_ms,
        engine_version=engine_version,
        git_sha=git_sha,
        confidence_weights_version=confidence_weights_version,
        force_correction_version=force_correction_version,
        boundary_model_version=boundary_model_version,
        boundary_model_sha256=boundary_model_sha256,
        tissue_model_version=tissue_model_version,
        tissue_model_sha256=tissue_model_sha256,
        probe_model_version=probe_model_version,
        probe_model_sha256=probe_model_sha256,
        input_hashes=input_hashes,
        intermediate_hashes=intermediate_hashes,
        config_hash=hash_bytes(config_payload),
        notes=notes,
    )
