"""Graft product recommendation logic.

Given a wound's measurements (with uncertainty), the wound classification,
and the product database, recommend specific products and sizes.

Logic:
1. Filter products to those indicated for the wound type and not contraindicated
2. For each indicated product, compute the required graft area using the
   product's IFU overlap (delta_p)
3. Pick the smallest stock size that meets recommended area
4. Sort by total cost (when cost data is present), break ties by overlap factor

The recommendation always shows multiple options so the clinician can
choose; never auto-selects.
"""

from __future__ import annotations

from dataclasses import dataclass

from woundscan.geometry.uncertainty import UncertaintyResult
from woundscan.graft.product_db import GraftProduct, ProductDatabase
from woundscan.graft.sizing import GraftSizing, compute_graft_size


@dataclass(frozen=True)
class GraftRecommendation:
    """A single product recommendation.

    Attributes
    ----------
    product : GraftProduct
    required_cm2 : float
        Computed required area (with 2-sigma margin).
    selected_size_cm2 : float
        Smallest stock size >= required_cm2; None if none available.
    sizing : GraftSizing
    rationale : str
    """

    product: GraftProduct
    required_cm2: float
    selected_size_cm2: float | None
    sizing: GraftSizing
    rationale: str


def recommend_grafts(
    surface_area_uncertainty: UncertaintyResult,
    perimeter_cm: float,
    perimeter_uncertainty_cm: float,
    wound_indication: str,
    product_db: ProductDatabase,
    contraindications: tuple[str, ...] = (),
) -> list[GraftRecommendation]:
    """Return ranked recommendations for the wound.

    Each indicated product gets one recommendation. Sorted by selected
    size ascending (smaller is generally cheaper and easier to apply).
    """
    candidates = product_db.list_by_indication(wound_indication)
    out: list[GraftRecommendation] = []
    for prod in candidates:
        if any(c in prod.contraindications for c in contraindications):
            continue
        sizing = compute_graft_size(
            surface_area_uncertainty,
            perimeter_cm,
            prod.overlap_delta_cm,
            perimeter_uncertainty_cm=perimeter_uncertainty_cm,
        )
        sizes = sorted(prod.available_sizes_cm2)
        selected: float | None = None
        for s in sizes:
            if s >= sizing.recommended_cm2:
                selected = s
                break
        rationale = (
            f"IFU overlap delta={prod.overlap_delta_cm}cm; "
            f"required={sizing.recommended_cm2:.2f}cm^2; "
            f"selected stock size={selected}"
        )
        out.append(
            GraftRecommendation(
                product=prod,
                required_cm2=sizing.recommended_cm2,
                selected_size_cm2=selected,
                sizing=sizing,
                rationale=rationale,
            )
        )

    out.sort(key=lambda r: (r.selected_size_cm2 is None, r.selected_size_cm2 or 1e9))
    return out
