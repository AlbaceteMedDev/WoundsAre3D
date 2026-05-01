"""Tamper-evident hash chain for the audit log.

Each audit log entry is hashed with the previous entry's hash, forming a
linked list. Tampering with any historical entry breaks the chain and is
detected by `verify_chain`. We do this in addition to S3 object lock as
defense in depth.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class HashChainEntry:
    """One link in the audit hash chain.

    Attributes
    ----------
    sequence : int
    payload_json : str
    previous_hash : str
        SHA-256 of the previous entry's serialized form, hex.
    self_hash : str
        SHA-256 of (previous_hash + payload_json).
    """

    sequence: int
    payload_json: str
    previous_hash: str
    self_hash: str


def compute_object_hash(obj: object) -> str:
    """Canonical JSON sha256 of any JSON-serializable object."""
    if hasattr(obj, "to_dict"):
        data = obj.to_dict()
    elif hasattr(obj, "__dict__"):
        data = obj.__dict__
    else:
        data = obj
    payload = json.dumps(data, sort_keys=True, default=str).encode()
    return hashlib.sha256(payload).hexdigest()


def append_to_chain(
    payload: dict, sequence: int, previous_hash: str
) -> HashChainEntry:
    """Build a new chain entry from a payload."""
    payload_json = json.dumps(payload, sort_keys=True)
    self_hash = hashlib.sha256(
        (previous_hash + payload_json).encode()
    ).hexdigest()
    return HashChainEntry(
        sequence=sequence,
        payload_json=payload_json,
        previous_hash=previous_hash,
        self_hash=self_hash,
    )


def verify_chain(entries: Iterable[HashChainEntry]) -> tuple[bool, int]:
    """Verify hash chain integrity.

    Returns (ok, last_valid_sequence). ok=False when any entry's hash
    doesn't match its claimed payload + predecessor.
    """
    prev = ""
    last_valid = -1
    expected_sequence = 0
    for entry in entries:
        if entry.sequence != expected_sequence:
            return False, last_valid
        if entry.previous_hash != prev:
            return False, last_valid
        expected = hashlib.sha256(
            (entry.previous_hash + entry.payload_json).encode()
        ).hexdigest()
        if expected != entry.self_hash:
            return False, last_valid
        prev = entry.self_hash
        last_valid = entry.sequence
        expected_sequence += 1
    return True, last_valid
