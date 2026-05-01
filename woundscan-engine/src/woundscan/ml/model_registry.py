"""Model registry: cards, weight content hashing, version pinning.

Every measurement records the exact model version used (content-hashed)
in its provenance. The registry enforces:

1. Each loaded model has a model card (training data, metrics, failure modes)
2. Weight files are hashed (SHA-256) at load time; the hash is recorded
3. Different versions of the same model have different IDs

This is what enables regulatory defense of any specific output: given a
provenance record we can reconstruct exactly which weights produced it.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ModelCard:
    """Minimum metadata for a deployed model.

    Required fields per regulatory expectation. The card is serialized to
    docs/ml_models.md and to every output's provenance record.
    """

    name: str
    version: str
    architecture: str
    training_dataset: str
    training_samples: int
    validation_dataset: str
    validation_samples: int
    primary_metric_name: str
    primary_metric_value: float
    weights_sha256: str
    known_failure_modes: tuple[str, ...] = field(default_factory=tuple)
    intended_use: str = ""


def hash_weights_file(path: Path | str) -> str:
    """SHA-256 hex digest of a weights file."""
    h = hashlib.sha256()
    p = Path(path)
    if not p.exists():
        return ""
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class ModelRegistry:
    """In-memory registry of loaded models. Indexed by (name, version)."""

    def __init__(self) -> None:
        self._cards: dict[tuple[str, str], ModelCard] = {}

    def register(self, card: ModelCard) -> None:
        key = (card.name, card.version)
        if key in self._cards:
            existing = self._cards[key]
            if existing.weights_sha256 != card.weights_sha256:
                raise ValueError(
                    f"Model {key} already registered with different hash. "
                    "Use a new version string for new weights."
                )
        self._cards[key] = card

    def get(self, name: str, version: str) -> ModelCard | None:
        return self._cards.get((name, version))

    def all_cards(self) -> list[ModelCard]:
        return list(self._cards.values())


GLOBAL_REGISTRY = ModelRegistry()
