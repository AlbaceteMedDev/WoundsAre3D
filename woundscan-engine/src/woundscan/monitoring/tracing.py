"""OpenTelemetry tracing.

Traces are exported to an OTLP collector in production. In dev/test the
exporter is a no-op so traces don't pollute logs.
"""

from __future__ import annotations

from contextlib import contextmanager


class _NoOpSpan:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def set_attribute(self, key: str, value: object) -> None:
        pass


class _NoOpTracer:
    @contextmanager
    def start_as_current_span(self, name: str):
        yield _NoOpSpan()


_tracer: object = _NoOpTracer()


def init_tracing(service_name: str = "woundscan-engine") -> None:
    """Initialize OTLP tracer. Falls back to no-op if SDK absent or not configured."""
    global _tracer
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource(attributes={"service.name": service_name})
        provider = TracerProvider(resource=resource)
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        except Exception:
            pass
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer(service_name)
    except ImportError:
        _tracer = _NoOpTracer()


def tracer():
    return _tracer
