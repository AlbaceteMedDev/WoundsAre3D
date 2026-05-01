"""Auth: identity, MFA, sessions, RBAC, audit logging."""

from __future__ import annotations

from woundscan.auth.audit_log import AuditAction, AuditLogger
from woundscan.auth.identity import (
    Identity,
    Role,
    User,
    hash_password,
    verify_password,
)
from woundscan.auth.mfa import generate_totp_secret, verify_totp_code
from woundscan.auth.rbac import Permission, has_permission
from woundscan.auth.sessions import (
    SESSION_TIMEOUT_MINUTES,
    Session,
    SessionStore,
    create_session,
    issue_jwt,
    verify_jwt,
)

__all__ = [
    "AuditAction",
    "AuditLogger",
    "Identity",
    "Permission",
    "Role",
    "SESSION_TIMEOUT_MINUTES",
    "Session",
    "SessionStore",
    "User",
    "create_session",
    "generate_totp_secret",
    "has_permission",
    "hash_password",
    "issue_jwt",
    "verify_jwt",
    "verify_password",
    "verify_totp_code",
]
