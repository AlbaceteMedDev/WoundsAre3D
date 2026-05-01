"""Prometheus metrics. Scraped by /metrics endpoint."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

METRIC_REQUEST_DURATION_S = Histogram(
    "woundscan_request_duration_seconds",
    "HTTP request duration",
    labelnames=("method", "route", "status"),
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

METRIC_FUSION_DURATION_S = Histogram(
    "woundscan_fusion_duration_seconds",
    "Gaussian-process fusion duration",
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)

METRIC_MEASUREMENTS_TOTAL = Counter(
    "woundscan_measurements_total",
    "Total measurements processed",
    labelnames=("organization", "wound_type", "quality_grade"),
)

METRIC_QUALITY_GRADE = Counter(
    "woundscan_quality_grade_total",
    "Number of measurements per quality grade",
    labelnames=("grade",),
)


def init_metrics() -> None:
    """Initialize collectors. Currently a no-op (Counter/Histogram self-init)."""


def record_quality_grade(grade: str) -> None:
    METRIC_QUALITY_GRADE.labels(grade=grade).inc()
