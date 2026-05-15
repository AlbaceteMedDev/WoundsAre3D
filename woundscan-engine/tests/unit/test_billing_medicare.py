"""Tests for billing/medicare reimbursement estimator."""

from __future__ import annotations

import pytest

from woundscan.billing.medicare import (
    DEFAULT_CONVERSION_FACTOR_2025,
    GPCI,
    MedicareEstimate,
    PlaceOfService,
    estimate_reimbursement,
)


class TestPlaceOfService:
    def test_office_is_non_facility(self):
        assert PlaceOfService.OFFICE.is_facility is False

    def test_outpatient_is_facility(self):
        assert PlaceOfService.OUTPATIENT.is_facility is True

    def test_snf_is_facility(self):
        assert PlaceOfService.SNF.is_facility is True

    def test_home_is_non_facility(self):
        assert PlaceOfService.HOME.is_facility is False


class TestEstimateReimbursement:
    def test_small_wound_one_primary_code_no_addons(self):
        est = estimate_reimbursement(
            applied_area_cm2=12.0,
            anatomic_region="trunk_arms_legs",
            pos=PlaceOfService.OFFICE,
            gpci=GPCI(),
        )
        assert est.primary_cpt == "15271"
        assert est.additional_cpt_units == 0
        assert est.additional_units_payment == 0
        assert est.total_payment > 0

    def test_larger_wound_triggers_addon_units(self):
        # 50 cm² → 25 cm² covered by primary + 1 add-on unit for the next 25.
        est = estimate_reimbursement(
            applied_area_cm2=50.0,
            anatomic_region="trunk_arms_legs",
            pos=PlaceOfService.OFFICE,
            gpci=GPCI(),
        )
        assert est.additional_cpt_units == 1

    def test_addon_rounding_is_ceiling(self):
        # 26 cm² → 1 cm² over the primary's 25 → CMS rounds up to 1 unit.
        est = estimate_reimbursement(
            applied_area_cm2=26.0,
            anatomic_region="trunk_arms_legs",
            pos=PlaceOfService.OFFICE,
            gpci=GPCI(),
        )
        assert est.additional_cpt_units == 1

    def test_face_scalp_digits_uses_15275_family(self):
        est = estimate_reimbursement(
            applied_area_cm2=10.0,
            anatomic_region="face_scalp_digits",
            pos=PlaceOfService.OUTPATIENT,
            gpci=GPCI(),
        )
        assert est.primary_cpt == "15275"

    def test_unknown_anatomic_region_raises(self):
        with pytest.raises(ValueError, match="Unknown anatomic_region"):
            estimate_reimbursement(
                applied_area_cm2=10.0,
                anatomic_region="elbow_left",
                pos=PlaceOfService.OFFICE,
                gpci=GPCI(),
            )

    def test_non_positive_area_raises(self):
        with pytest.raises(ValueError, match="applied_area_cm2 must be positive"):
            estimate_reimbursement(
                applied_area_cm2=0.0,
                anatomic_region="trunk_arms_legs",
                pos=PlaceOfService.OFFICE,
                gpci=GPCI(),
            )

    def test_office_pays_more_than_facility(self):
        # Non-facility PE RVU is larger (practice carries overhead) →
        # higher CPT payment when site is office.
        common = dict(
            applied_area_cm2=20.0,
            anatomic_region="trunk_arms_legs",
            gpci=GPCI(),
        )
        office = estimate_reimbursement(**common, pos=PlaceOfService.OFFICE)
        outpt = estimate_reimbursement(**common, pos=PlaceOfService.OUTPATIENT)
        assert office.total_payment > outpt.total_payment

    def test_drug_payment_uses_package_size_for_single_use(self):
        # 60 cm² applied from a 100 cm² package → drug paid on 100 cm².
        asp = 130.0  # $/cm²
        est = estimate_reimbursement(
            applied_area_cm2=60.0,
            anatomic_region="trunk_arms_legs",
            pos=PlaceOfService.OFFICE,
            gpci=GPCI(),
            drug_asp_per_cm2=asp,
            package_size_cm2=100.0,
        )
        assert est.drug_payment == pytest.approx(100.0 * asp, abs=0.01)
        # Wastage note should appear.
        assert any("Wastage" in n for n in est.notes)

    def test_drug_payment_falls_back_to_applied_area_when_no_package(self):
        asp = 50.0
        est = estimate_reimbursement(
            applied_area_cm2=20.0,
            anatomic_region="trunk_arms_legs",
            pos=PlaceOfService.OFFICE,
            gpci=GPCI(),
            drug_asp_per_cm2=asp,
        )
        assert est.drug_payment == pytest.approx(20.0 * asp, abs=0.01)
        assert not any("Wastage" in n for n in est.notes)

    def test_gpci_scales_payment_linearly(self):
        common = dict(
            applied_area_cm2=20.0,
            anatomic_region="trunk_arms_legs",
            pos=PlaceOfService.OFFICE,
        )
        baseline = estimate_reimbursement(**common, gpci=GPCI(work=1.0, practice_expense=1.0, malpractice=1.0))
        high = estimate_reimbursement(
            **common, gpci=GPCI(work=1.5, practice_expense=1.5, malpractice=1.5)
        )
        # All RVU components scaled 1.5× → primary CPT payment scales 1.5× too.
        assert high.primary_cpt_payment == pytest.approx(baseline.primary_cpt_payment * 1.5, rel=0.001)

    def test_facility_pos_emits_facility_note(self):
        est = estimate_reimbursement(
            applied_area_cm2=20.0,
            anatomic_region="trunk_arms_legs",
            pos=PlaceOfService.OUTPATIENT,
            gpci=GPCI(),
        )
        assert any("Facility POS" in n for n in est.notes)

    def test_custom_conversion_factor_respected(self):
        common = dict(
            applied_area_cm2=20.0,
            anatomic_region="trunk_arms_legs",
            pos=PlaceOfService.OFFICE,
            gpci=GPCI(),
        )
        default_cf = estimate_reimbursement(**common)
        half_cf = estimate_reimbursement(
            **common, conversion_factor=DEFAULT_CONVERSION_FACTOR_2025 / 2
        )
        assert half_cf.primary_cpt_payment == pytest.approx(default_cf.primary_cpt_payment / 2, rel=0.001)

    def test_breakdown_contains_expected_keys(self):
        est = estimate_reimbursement(
            applied_area_cm2=30.0,
            anatomic_region="trunk_arms_legs",
            pos=PlaceOfService.OFFICE,
            gpci=GPCI(),
            drug_asp_per_cm2=10.0,
        )
        assert isinstance(est, MedicareEstimate)
        for key in (
            "primary_cpt_breakdown",
            "addon_cpt_breakdown",
            "addon_units",
            "drug_billable_cm2",
            "drug_asp_per_cm2",
        ):
            assert key in est.breakdown
        assert est.breakdown["primary_cpt_breakdown"]["total_rvu"] > 0
