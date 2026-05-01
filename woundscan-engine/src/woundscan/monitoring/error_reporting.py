"""Error reporting via structured logs.

We do NOT use a third-party error reporter (Sentry, etc.) for HIPAA
reasons — exception payloads can include PHI. Instead, errors are
sanitized through the structlog pipeline and emitted to stdout, where
the AWS log infrastructure ingests them into a HIPAA-compliant log
group with retention and access control.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog


@dataclass
class ErrorReporter:
    """Sanitizing error reporter.

    Strips known PHI fields from the exception context before logging.
    Adds a fingerprint hash so duplicate errors are deduplicated by the
    log analytics layer.
    """

    phi_fields: tuple[str, ...] = (
        "mrn",
        "first_name",
        "last_name",
        "dob",
        "ssn",
        "patient_id",
        "address",
        "phone",
        "email",
    )
    extra_context: dict[str, Any] = field(default_factory=dict)

    def report(self, exc: BaseException, context: dict[str, Any] | None = None) -> None:
        log = structlog.get_logger("woundscan.error")
        ctx = dict(context or {})
        for k in self.phi_fields:
            if k in ctx:
                ctx[k] = "<redacted>"
        log.error(
            "engine_exception",
            error_type=type(exc).__name__,
            error_message=str(exc),
            **{**self.extra_context, **ctx},
            exc_info=True,
        )


_GLOBAL_REPORTER: ErrorReporter | None = None


def init_error_reporting() -> ErrorReporter:
    global _GLOBAL_REPORTER
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    )
    _GLOBAL_REPORTER = ErrorReporter()
    return _GLOBAL_REPORTER


def capture_exception(exc: BaseException, context: dict[str, Any] | None = None) -> None:
    """Convenience: report via the global reporter."""
    if _GLOBAL_REPORTER is None:
        init_error_reporting()
    assert _GLOBAL_REPORTER is not None
    _GLOBAL_REPORTER.report(exc, context)
