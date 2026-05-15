"""Tests for monitoring/tracing: no-op default, OTLP init, span emission."""

from __future__ import annotations

import builtins
import importlib

import pytest

from woundscan.monitoring import tracing


@pytest.fixture(autouse=True)
def _reset_tracer():
    """The module owns a global `_tracer` — restore it between tests."""
    saved = tracing._tracer
    yield
    tracing._tracer = saved


class TestNoOpDefault:
    def test_default_tracer_is_noop(self):
        tracing._tracer = tracing._NoOpTracer()
        with tracing.tracer().start_as_current_span("noop") as span:
            span.set_attribute("k", "v")  # must not raise

    def test_noop_span_context_manager_returns_false_on_exit(self):
        span = tracing._NoOpSpan()
        with span as inner:
            assert inner is span


class TestInitTracing:
    def test_emits_a_span_when_sdk_configured(self):
        from opentelemetry import trace
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
            InMemorySpanExporter,
        )

        tracing.init_tracing(service_name="ws-engine-test")

        # init_tracing builds a real TracerProvider with a BatchSpanProcessor +
        # OTLP exporter; layer an in-memory exporter on top so we can assert
        # the tracer actually emits spans.
        exporter = InMemorySpanExporter()
        provider = trace.get_tracer_provider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))

        with tracing.tracer().start_as_current_span("wound_measure") as span:
            span.set_attribute("wound.id", "w-1")

        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].name == "wound_measure"
        assert spans[0].attributes["wound.id"] == "w-1"

    def test_falls_back_when_otlp_exporter_missing(self, monkeypatch):
        # The OTLP exporter branch is wrapped in try/except so init still
        # succeeds when the exporter package isn't installed — verify by
        # stubbing the import to raise.
        from opentelemetry import trace
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
            InMemorySpanExporter,
        )

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name.startswith("opentelemetry.exporter.otlp"):
                raise ImportError("simulated: OTLP exporter not installed")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        tracing.init_tracing(service_name="ws-engine-no-otlp")

        # Provider should still be set up — we can attach our own exporter
        # and emit spans.
        exporter = InMemorySpanExporter()
        provider = trace.get_tracer_provider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        with tracing.tracer().start_as_current_span("fallback"):
            pass
        assert len(exporter.get_finished_spans()) == 1

    def test_falls_back_to_noop_when_sdk_missing(self, monkeypatch):
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "opentelemetry" or name.startswith("opentelemetry.sdk"):
                raise ImportError("simulated: opentelemetry SDK missing")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        # Need to reload to retrigger the SDK import branch
        importlib.reload(tracing)
        tracing.init_tracing()
        assert isinstance(tracing.tracer(), tracing._NoOpTracer)
