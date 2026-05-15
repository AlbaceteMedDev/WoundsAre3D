"""Tests for ml/model_registry: cards, hashing, registry CRUD."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from woundscan.ml.model_registry import (
    GLOBAL_REGISTRY,
    ModelCard,
    ModelRegistry,
    hash_weights_file,
)


def _card(**overrides) -> ModelCard:
    base = dict(
        name="boundary_seg",
        version="1.0.0",
        architecture="UNet",
        training_dataset="aza-2024-q4",
        training_samples=4321,
        validation_dataset="aza-val",
        validation_samples=512,
        primary_metric_name="iou",
        primary_metric_value=0.91,
        weights_sha256="a" * 64,
        known_failure_modes=("dark skin tones underrepresented",),
        intended_use="Initial boundary proposal; clinician edits before submission.",
    )
    base.update(overrides)
    return ModelCard(**base)


class TestHashWeightsFile:
    def test_returns_sha256_of_contents(self, tmp_path: Path):
        p = tmp_path / "weights.bin"
        p.write_bytes(b"hello wound scan")
        expected = hashlib.sha256(b"hello wound scan").hexdigest()
        assert hash_weights_file(p) == expected

    def test_empty_string_for_missing_file(self, tmp_path: Path):
        assert hash_weights_file(tmp_path / "absent.bin") == ""

    def test_accepts_str_or_path(self, tmp_path: Path):
        p = tmp_path / "w.bin"
        p.write_bytes(b"x")
        assert hash_weights_file(str(p)) == hashlib.sha256(b"x").hexdigest()
        assert hash_weights_file(p) == hash_weights_file(str(p))

    def test_chunks_large_files(self, tmp_path: Path):
        # 3 MB file forces multiple 1 MB chunk reads in the hashing loop.
        p = tmp_path / "big.bin"
        data = b"\x00" * (3 * 1024 * 1024)
        p.write_bytes(data)
        assert hash_weights_file(p) == hashlib.sha256(data).hexdigest()


class TestModelRegistry:
    def test_register_and_get_round_trip(self):
        reg = ModelRegistry()
        c = _card()
        reg.register(c)
        assert reg.get("boundary_seg", "1.0.0") is c

    def test_get_returns_none_for_unknown(self):
        reg = ModelRegistry()
        assert reg.get("missing", "0") is None

    def test_re_register_with_same_hash_is_idempotent(self):
        reg = ModelRegistry()
        c = _card()
        reg.register(c)
        reg.register(c)
        assert len(reg.all_cards()) == 1

    def test_re_register_with_different_hash_raises(self):
        reg = ModelRegistry()
        reg.register(_card(weights_sha256="a" * 64))
        with pytest.raises(ValueError, match="different hash"):
            reg.register(_card(weights_sha256="b" * 64))

    def test_different_versions_coexist(self):
        reg = ModelRegistry()
        reg.register(_card(version="1.0.0", weights_sha256="a" * 64))
        reg.register(_card(version="1.0.1", weights_sha256="b" * 64))
        assert len(reg.all_cards()) == 2

    def test_all_cards_returns_list_copy(self):
        reg = ModelRegistry()
        reg.register(_card())
        cards = reg.all_cards()
        cards.clear()
        # Internal state must be unaffected by mutating the returned list.
        assert len(reg.all_cards()) == 1


def test_global_registry_is_a_registry_instance():
    assert isinstance(GLOBAL_REGISTRY, ModelRegistry)
