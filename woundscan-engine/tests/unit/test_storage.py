"""Tests for storage tamper-evidence."""
import pytest

from woundscan.storage.tamper_evidence import (
    HashChainEntry,
    append_to_chain,
    compute_object_hash,
    verify_chain,
)


class TestHashChain:
    def test_empty_chain_verifies(self):
        ok, last = verify_chain([])
        assert ok and last == -1

    def test_single_entry_chain(self):
        e = append_to_chain({"a": 1}, sequence=0, previous_hash="")
        ok, last = verify_chain([e])
        assert ok and last == 0

    def test_three_entry_chain(self):
        e0 = append_to_chain({"k": 0}, 0, "")
        e1 = append_to_chain({"k": 1}, 1, e0.self_hash)
        e2 = append_to_chain({"k": 2}, 2, e1.self_hash)
        ok, last = verify_chain([e0, e1, e2])
        assert ok and last == 2

    def test_tampered_payload_fails(self):
        e0 = append_to_chain({"k": 0}, 0, "")
        tampered = HashChainEntry(
            sequence=e0.sequence,
            payload_json='{"k": 99}',  # tamper
            previous_hash=e0.previous_hash,
            self_hash=e0.self_hash,
        )
        ok, _ = verify_chain([tampered])
        assert not ok

    def test_skipped_sequence_fails(self):
        e0 = append_to_chain({"k": 0}, 0, "")
        e2 = append_to_chain({"k": 2}, 2, e0.self_hash)
        ok, _ = verify_chain([e0, e2])
        assert not ok


class TestObjectHash:
    def test_consistent_hash(self):
        a = {"x": 1, "y": 2}
        b = {"y": 2, "x": 1}
        assert compute_object_hash(a) == compute_object_hash(b)

    def test_different_objects_different_hash(self):
        assert compute_object_hash({"a": 1}) != compute_object_hash({"a": 2})
