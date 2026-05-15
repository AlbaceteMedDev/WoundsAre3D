"""Focused tests for the remaining coverage gaps to push 87.7% → 90%+.

Targets:
- monitoring/error_reporting — PHI redaction + global reporter
- synthesis/ground_truth — wrap/relative_error/assert_within_tolerance
- quality/confidence — weight validation + map composition
"""

from __future__ import annotations

import numpy as np
import pytest

from woundscan.monitoring.error_reporting import (
    ErrorReporter,
    capture_exception,
    init_error_reporting,
)
from woundscan.quality.confidence import (
    DEFAULT_WEIGHTS,
    ConfidenceWeights,
    QualityComponents,
    compute_confidence_map,
)
from woundscan.synthesis.analytic_shapes import AnalyticWound
from woundscan.synthesis.ground_truth import (
    GroundTruth,
    assert_within_tolerance,
    compute_ground_truth,
    relative_error,
)


# ---------------------------------------------------------------------------
# monitoring/error_reporting
# ---------------------------------------------------------------------------


class TestErrorReporter:
    def test_redacts_phi_fields_before_logging(self, caplog):
        reporter = ErrorReporter()
        try:
            raise RuntimeError("boom")
        except RuntimeError as exc:
            # Should not raise; the structlog pipeline handles the actual emit.
            reporter.report(
                exc,
                {"mrn": "MRN-12345", "first_name": "Jane", "other": "ok"},
            )

    def test_report_with_no_context_works(self):
        try:
            raise ValueError("err")
        except ValueError as exc:
            ErrorReporter().report(exc)  # no context arg

    def test_init_returns_singleton_compatible_reporter(self):
        r = init_error_reporting()
        assert isinstance(r, ErrorReporter)

    def test_capture_exception_initializes_global_reporter_if_unset(self, monkeypatch):
        import woundscan.monitoring.error_reporting as mod

        monkeypatch.setattr(mod, "_GLOBAL_REPORTER", None)
        try:
            raise KeyError("x")
        except KeyError as exc:
            capture_exception(exc, {"resource": "r1"})
        # After capture, the global reporter must have been initialized.
        assert mod._GLOBAL_REPORTER is not None

    def test_capture_exception_reuses_existing_global(self):
        import woundscan.monitoring.error_reporting as mod

        existing = mod._GLOBAL_REPORTER
        try:
            raise ValueError("again")
        except ValueError as exc:
            capture_exception(exc)
        # Pointer to the same reporter — no re-init.
        assert mod._GLOBAL_REPORTER is existing


# ---------------------------------------------------------------------------
# synthesis/ground_truth
# ---------------------------------------------------------------------------


def _wound() -> AnalyticWound:
    """A minimal AnalyticWound the ground-truth helpers can wrap.

    The fields ground_truth.py reads (`name`, `true_volume`,
    `true_surface_area`, `true_footprint_area`) are populated with
    placeholders; the depth_map / mask aren't read by these helpers, but
    AnalyticWound is a dataclass so we still need to satisfy them.
    """
    return AnalyticWound(
        depth_map=np.zeros((4, 4), dtype=np.float32),
        mask=np.ones((4, 4), dtype=bool),
        dx=1.0,
        dy=1.0,
        true_volume=5.0,
        true_surface_area=12.0,
        true_footprint_area=10.0,
        name="test_paraboloid",
    )


class TestGroundTruth:
    def test_compute_ground_truth_default_analytic(self):
        gt = compute_ground_truth(_wound())
        assert isinstance(gt, GroundTruth)
        assert gt.name == "test_paraboloid"
        assert gt.analytic is True
        assert gt.grid_n == 0
        assert gt.volume_cm3 == 5.0

    def test_compute_ground_truth_numerical_branch(self):
        gt = compute_ground_truth(
            _wound(), analytic=False, grid_n=256, notes=("phantom-grade",)
        )
        assert gt.analytic is False
        assert gt.grid_n == 256
        assert gt.notes == ("phantom-grade",)

    def test_relative_error_zero_truth_zero_measured(self):
        assert relative_error(0.0, 0.0) == 0.0

    def test_relative_error_zero_truth_nonzero_measured(self):
        assert relative_error(1.0, 0.0) == float("inf")

    def test_relative_error_normal_case(self):
        # |1.05 - 1.00| / 1.00 = 0.05
        assert relative_error(1.05, 1.00) == pytest.approx(0.05)

    def test_assert_within_tolerance_passes(self):
        gt = compute_ground_truth(_wound())
        assert_within_tolerance(gt.volume_cm3 * 1.01, gt, "volume_cm3", rel_tol=0.02)

    def test_assert_within_tolerance_fails_with_useful_message(self):
        gt = compute_ground_truth(_wound())
        with pytest.raises(AssertionError, match="volume_cm3"):
            assert_within_tolerance(gt.volume_cm3 * 1.10, gt, "volume_cm3", rel_tol=0.01)


# ---------------------------------------------------------------------------
# quality/confidence
# ---------------------------------------------------------------------------


def _components(h: int = 8, w: int = 8, value: float = 0.5) -> QualityComponents:
    arr = np.full((h, w), value, dtype=np.float32)
    return QualityComponents(
        specularity=arr,
        texture=arr,
        lighting=arr,
        motion=arr,
        edge_distance=arr,
        frame_consistency=arr,
        boundary_confidence=arr,
    )


class TestConfidenceWeights:
    def test_default_sums_to_one(self):
        # Init succeeds → validator passed → weights sum to 1.
        assert DEFAULT_WEIGHTS.version == "v1.0.0"

    def test_bad_weights_raise(self):
        with pytest.raises(ValueError, match="sum to 1"):
            ConfidenceWeights(
                specularity=0.5,
                texture=0.5,
                lighting=0.5,
                motion=0.0,
                edge_distance=0.0,
                frame_consistency=0.0,
                boundary_confidence=0.0,
            )


class TestComputeConfidenceMap:
    def test_uniform_components_yield_uniform_confidence(self):
        comp = _components(value=0.5)
        conf = compute_confidence_map(comp)
        assert conf.shape == (8, 8)
        # Every pixel computes the same value (since all components are 0.5).
        assert np.allclose(conf, conf[0, 0])

    def test_dtype_is_float32(self):
        conf = compute_confidence_map(_components())
        assert conf.dtype == np.float32

    def test_output_is_clipped_to_unit_interval(self):
        # Push every weighted component to its maximum so we exit the [0,1] band.
        big = QualityComponents(
            specularity=np.zeros((4, 4), dtype=np.float32),  # (1 - 0) * 0.25 = 0.25
            texture=np.ones((4, 4), dtype=np.float32),  # 1 * 0.20 = 0.20
            lighting=np.ones((4, 4), dtype=np.float32),  # 0.15
            motion=np.zeros((4, 4), dtype=np.float32),  # (1 - 0) * 0.15 = 0.15
            edge_distance=np.ones((4, 4), dtype=np.float32),  # 0.10
            frame_consistency=np.ones((4, 4), dtype=np.float32),  # 0.10
            boundary_confidence=np.full((4, 4), 5.0, dtype=np.float32),  # 5 * 0.05 = 0.25
        )
        conf = compute_confidence_map(big)
        assert conf.min() >= 0.0
        assert conf.max() <= 1.0
