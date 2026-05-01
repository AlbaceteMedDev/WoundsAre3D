"""Monitoring: metrics, tracing, error reporting."""

from __future__ import annotations

from woundscan.monitoring.error_reporting import (
    ErrorReporter,
    capture_exception,
    init_error_reporting,
)
from woundscan.monitoring.metrics import (
    METRIC_FUSION_DURATION_S,
    METRIC_MEASUREMENTS_TOTAL,
    METRIC_QUALITY_GRADE,
    METRIC_REQUEST_DURATION_S,
    init_metrics,
    record_quality_grade,
)
from woundscan.monitoring.tracing import init_tracing, tracer

__all__ = [
    "ErrorReporter",
    "METRIC_FUSION_DURATION_S",
    "METRIC_MEASUREMENTS_TOTAL",
    "METRIC_QUALITY_GRADE",
    "METRIC_REQUEST_DURATION_S",
    "capture_exception",
    "init_error_reporting",
    "init_metrics",
    "init_tracing",
    "record_quality_grade",
    "tracer",
]
