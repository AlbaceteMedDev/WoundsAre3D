"""Audit logger dependency."""
from __future__ import annotations

from woundscan.auth.audit_log import AuditLogger

_GLOBAL_AUDIT = AuditLogger()


def get_audit_logger() -> AuditLogger:
    return _GLOBAL_AUDIT
