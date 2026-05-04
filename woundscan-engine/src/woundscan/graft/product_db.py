"""Skin substitute graft product database.

Each product carries:
- IFU-mandated overlap onto periwound (delta)
- Available stock sizes
- Cost (used in recommendation when multiple products fit)
- Indications (which wound types it's approved for)

The default DB ships with a representative set of products. Production
deployments load the actual contracted product list from the admin UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GraftProduct:
    """A single graft product offering.

    Attributes
    ----------
    id : str
    name : str
    manufacturer : str
    overlap_delta_cm : float
        Required overlap onto periwound per IFU.
    available_sizes_cm2 : tuple[float, ...]
        Stock sizes the product is sold in.
    indications : tuple[str, ...]
        Wound type indications (e.g. "DFU", "VLU").
    contraindications : tuple[str, ...]
    notes : str
    """

    id: str
    name: str
    manufacturer: str
    overlap_delta_cm: float
    available_sizes_cm2: tuple[float, ...]
    indications: tuple[str, ...]
    contraindications: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""


@dataclass
class ProductDatabase:
    products: dict[str, GraftProduct] = field(default_factory=dict)

    def add(self, product: GraftProduct) -> None:
        self.products[product.id] = product

    def get(self, product_id: str) -> GraftProduct | None:
        return self.products.get(product_id)

    def list_by_indication(self, indication: str) -> list[GraftProduct]:
        return [p for p in self.products.values() if indication in p.indications]


def default_product_db() -> ProductDatabase:
    """Representative built-in catalog. Replace with contracted list at deploy."""
    db = ProductDatabase()
    db.add(
        GraftProduct(
            id="ALG-DUO-S",
            name="AlgiDuo Small",
            manufacturer="Acme Bio",
            overlap_delta_cm=0.5,
            available_sizes_cm2=(2.0, 4.0, 8.0, 16.0),
            indications=("DFU", "VLU", "PressureInjury"),
        )
    )
    db.add(
        GraftProduct(
            id="ALG-DUO-L",
            name="AlgiDuo Large",
            manufacturer="Acme Bio",
            overlap_delta_cm=0.5,
            available_sizes_cm2=(25.0, 50.0, 100.0),
            indications=("DFU", "VLU", "PressureInjury"),
        )
    )
    db.add(
        GraftProduct(
            id="DERM-MAT-2",
            name="DermMatrix 2cm overlap",
            manufacturer="DermCorp",
            overlap_delta_cm=2.0,
            available_sizes_cm2=(4.0, 9.0, 16.0, 25.0, 49.0, 100.0),
            indications=("DFU", "VLU", "PressureInjury", "Surgical"),
        )
    )
    db.add(
        GraftProduct(
            id="AMNI-X",
            name="AmniX Membrane",
            manufacturer="HeritagePlacenta",
            overlap_delta_cm=0.3,
            available_sizes_cm2=(1.0, 4.0, 9.0, 16.0),
            indications=("DFU", "VLU"),
            contraindications=("ActiveInfection",),
        )
    )
    return db
