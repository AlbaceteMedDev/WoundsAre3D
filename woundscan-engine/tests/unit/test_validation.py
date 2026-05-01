"""Tests for validation: consistency, plausibility, quality grade, phantom calibration."""
import numpy as np
import pytest
from datetime import datetime, timezone

from woundscan.validation.consistency import check_camera_probe_agreement
from woundscan.validation.phantom_calibration import (
    PhantomCalibration,
    PhantomScan,
    record_phantom_scan,
)
from woundscan.validation.plausibility import (
    all_passed,
    run_geometric_plausibility_checks,
)
from woundscan.validation.quality_score import QualityGrade, compute_quality_grade
from woundscan.validation.temporal_plausibility import check_temporal_plausibility


class TestPlausibility:
    def test_normal_passes(self):
        checks = run_geometric_plausibility_checks(
            volume_cm3=2.0,
            surface_area_cm2=5.0,
            footprint_area_cm2=4.0,
            max_depth_cm=1.0,
            mean_depth_cm=0.5,
        )
        assert all_passed(checks)

    def test_negative_volume_fails(self):
        checks = run_geometric_plausibility_checks(
            volume_cm3=-1.0,
            surface_area_cm2=5.0,
            footprint_area_cm2=4.0,
            max_depth_cm=1.0,
            mean_depth_cm=0.5,
        )
        assert not all_passed(checks)
        assert any(c.name == "volume_nonneg" and not c.passed for c in checks)

    def test_huge_depth_fails(self):
        checks = run_geometric_plausibility_checks(
            volume_cm3=10.0,
            surface_area_cm2=5.0,
            footprint_area_cm2=4.0,
            max_depth_cm=20.0,
            mean_depth_cm=2.0,
        )
        assert not all_passed(checks)


class TestTemporalPlausibility:
    def test_no_prior_data_skipped(self):
        checks = check_temporal_plausibility(
            current_volume_cm3=10.0,
            current_area_cm2=20.0,
            days_since_last_visit=7.0,
            last_volume_cm3=None,
            last_area_cm2=None,
        )
        assert checks[0].name == "temporal_skipped"

    def test_implausible_change_flagged(self):
        checks = check_temporal_plausibility(
            current_volume_cm3=20.0,
            current_area_cm2=30.0,
            days_since_last_visit=1.0,
            last_volume_cm3=10.0,  # +100% in 1 day
            last_area_cm2=15.0,
        )
        assert any(not c.passed for c in checks)


class TestQualityGrade:
    def test_a_grade_perfect_inputs(self):
        report = compute_quality_grade(
            mean_confidence=0.95,
            n_probe_anchors=12,
            camera_probe_max_z=0.5,
            fiducial_detected_count=4,
            fiducial_max_reprojection_pix=0.3,
            frame_consistency_mean=0.95,
            ml_segmentation_confidence=0.9,
            photo_focus_score=1.0,
        )
        assert report.grade == QualityGrade.A

    def test_f_grade_terrible_inputs(self):
        report = compute_quality_grade(
            mean_confidence=0.2,
            n_probe_anchors=2,
            camera_probe_max_z=8.0,
            fiducial_detected_count=0,
            fiducial_max_reprojection_pix=10.0,
            frame_consistency_mean=0.2,
            ml_segmentation_confidence=0.3,
            photo_focus_score=0.2,
        )
        assert report.grade == QualityGrade.F
        assert report.recommendation == "recapture_recommended"


class TestConsistency:
    def test_perfect_agreement(self):
        x_axis = np.linspace(0, 10, 11)
        y_axis = np.linspace(0, 10, 11)
        X, Y = np.meshgrid(x_axis, y_axis)
        depth = np.full_like(X, 5.0)
        sigma = np.full_like(X, 0.5)

        probe_x = np.array([2.0, 5.0, 8.0])
        probe_y = np.array([3.0, 5.0, 7.0])
        probe_d = np.array([5.0, 5.0, 5.0])
        probe_s = np.array([0.5, 0.5, 0.5])

        result = check_camera_probe_agreement(
            probe_x, probe_y, probe_d, probe_s,
            X, Y, depth, sigma,
        )
        assert result.overall_passed

    def test_disagreement_fails(self):
        x_axis = np.linspace(0, 10, 11)
        y_axis = np.linspace(0, 10, 11)
        X, Y = np.meshgrid(x_axis, y_axis)
        depth = np.full_like(X, 5.0)
        sigma = np.full_like(X, 0.5)
        probe_x = np.array([5.0])
        probe_y = np.array([5.0])
        probe_d = np.array([20.0])  # way off
        probe_s = np.array([0.5])
        result = check_camera_probe_agreement(
            probe_x, probe_y, probe_d, probe_s, X, Y, depth, sigma
        )
        assert not result.overall_passed


class TestPhantomCalibration:
    def test_drift_alert(self):
        cal = PhantomCalibration(clinician_id="c1")
        scan = PhantomScan(
            phantom_id="P1",
            clinician_id="c1",
            timestamp=datetime.now(timezone.utc),
            measured_volume_cm3=1.10,
            measured_surface_area_cm2=2.10,
            true_volume_cm3=1.0,
            true_surface_area_cm2=2.0,
        )
        record_phantom_scan(cal, scan)
        assert cal.in_drift_alert()

    def test_no_drift_when_close(self):
        cal = PhantomCalibration(clinician_id="c1")
        scan = PhantomScan(
            phantom_id="P1",
            clinician_id="c1",
            timestamp=datetime.now(timezone.utc),
            measured_volume_cm3=1.005,
            measured_surface_area_cm2=2.005,
            true_volume_cm3=1.0,
            true_surface_area_cm2=2.0,
        )
        record_phantom_scan(cal, scan)
        assert not cal.in_drift_alert()
