"""Tests for graft sizing and recommendation."""
import numpy as np
import pytest

from woundscan.geometry.uncertainty import UncertaintyResult
from woundscan.graft.product_db import default_product_db
from woundscan.graft.recommendation import recommend_grafts
from woundscan.graft.sizing import compute_graft_size


class TestGraftSizing:
    def test_recommendation_above_point_estimate(self):
        sa = UncertaintyResult(
            mean=10.0, std=0.5, ci_95_low=9.0, ci_95_high=11.0, median=10.0, n_samples=1000
        )
        sizing = compute_graft_size(sa, perimeter_cm=12.0, overlap_delta_cm=0.5)
        # Recommendation includes 2-sigma upper bound
        assert sizing.recommended_cm2 > sizing.point_estimate_cm2

    def test_zero_overlap_equals_surface_area(self):
        sa = UncertaintyResult(
            mean=10.0, std=0.0, ci_95_low=10.0, ci_95_high=10.0, median=10.0, n_samples=1000
        )
        sizing = compute_graft_size(sa, perimeter_cm=12.0, overlap_delta_cm=0.0)
        assert abs(sizing.point_estimate_cm2 - 10.0) < 0.01

    def test_overlap_increases_size(self):
        sa = UncertaintyResult(
            mean=10.0, std=0.0, ci_95_low=10.0, ci_95_high=10.0, median=10.0, n_samples=1000
        )
        s1 = compute_graft_size(sa, perimeter_cm=12.0, overlap_delta_cm=0.5)
        s2 = compute_graft_size(sa, perimeter_cm=12.0, overlap_delta_cm=2.0)
        assert s2.point_estimate_cm2 > s1.point_estimate_cm2


class TestRecommendation:
    def test_recommends_for_indication(self):
        sa = UncertaintyResult(
            mean=5.0, std=0.3, ci_95_low=4.4, ci_95_high=5.6, median=5.0, n_samples=300
        )
        recs = recommend_grafts(
            surface_area_uncertainty=sa,
            perimeter_cm=8.0,
            perimeter_uncertainty_cm=0.2,
            wound_indication="DFU",
            product_db=default_product_db(),
        )
        assert len(recs) > 0
        for r in recs:
            assert "DFU" in r.product.indications

    def test_contraindication_excludes_product(self):
        sa = UncertaintyResult(
            mean=5.0, std=0.3, ci_95_low=4.4, ci_95_high=5.6, median=5.0, n_samples=300
        )
        all_recs = recommend_grafts(
            surface_area_uncertainty=sa,
            perimeter_cm=8.0,
            perimeter_uncertainty_cm=0.2,
            wound_indication="DFU",
            product_db=default_product_db(),
        )
        infected_recs = recommend_grafts(
            surface_area_uncertainty=sa,
            perimeter_cm=8.0,
            perimeter_uncertainty_cm=0.2,
            wound_indication="DFU",
            product_db=default_product_db(),
            contraindications=("ActiveInfection",),
        )
        # Filtering should remove AmniX
        assert len(infected_recs) < len(all_recs)
