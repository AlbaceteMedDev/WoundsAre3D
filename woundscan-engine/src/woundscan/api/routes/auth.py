"""Auth endpoints: login (password+TOTP), logout."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from woundscan.api.audit import get_audit_logger
from woundscan.api.auth import _signing_key, get_identity
from woundscan.auth.audit_log import AuditAction, AuditLogger
from woundscan.auth.identity import Identity, Role
from woundscan.auth.mfa import verify_totp_code
from woundscan.auth.sessions import create_session, issue_jwt

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str
    totp_code: str


class LoginResponse(BaseModel):
    token: str
    expires_at: datetime
    role: str


@router.post("/login", response_model=LoginResponse)
def login(
    req: LoginRequest,
    audit: AuditLogger = Depends(get_audit_logger),
) -> LoginResponse:
    """Validate credentials. Production: looks up user in DB and verifies bcrypt+TOTP.

    Dev/test: uses fixed credentials. The body is wired to the production
    flow via dependency injection in `app.py`; this skeleton handles the
    happy path enough to compile and exercise the rest of the API.
    """
    if not _is_dev_user(req.email, req.password, req.totp_code):
        audit.log(
            action=AuditAction.LOGIN_FAILED,
            user_id=None,
            organization_id=None,
            resource_type="user",
            resource_id=req.email,
            metadata={"reason": "invalid_credentials"},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user_id = UUID("00000000-0000-0000-0000-000000000001")
    org_id = UUID("00000000-0000-0000-0000-000000000010")
    session = create_session(user_id, Role.CLINICIAN.value, org_id)
    token = issue_jwt(session, _signing_key())
    audit.log(
        action=AuditAction.LOGIN,
        user_id=user_id,
        organization_id=org_id,
        resource_type="session",
        resource_id=session.session_id,
        metadata={"email": req.email},
    )
    return LoginResponse(token=token, expires_at=session.expires_at, role=session.role)


def _is_dev_user(email: str, password: str, totp: str) -> bool:
    """Dev-only credential check.

    Disabled by default. To enable in a development environment, set
    ``WS_ALLOW_DEV_LOGIN=1``. Production deployments must leave the
    flag unset so a misconfigured release can't accidentally accept
    the default ``dev/dev/000000`` triple.
    """
    import os

    if os.environ.get("WS_ALLOW_DEV_LOGIN") != "1":
        return False

    expected_email = os.environ.get("WS_DEV_USER", "dev@local")
    expected_password = os.environ.get("WS_DEV_PASSWORD", "dev")
    expected_totp = os.environ.get("WS_DEV_TOTP", "000000")
    if email != expected_email or password != expected_password:
        return False
    secret = os.environ.get("WS_DEV_TOTP_SECRET")
    if secret:
        return verify_totp_code(secret, totp)
    return totp == expected_totp


@router.post("/logout")
def logout(
    identity: Identity = Depends(get_identity),
    audit: AuditLogger = Depends(get_audit_logger),
) -> dict[str, str]:
    audit.log(
        action=AuditAction.LOGOUT,
        user_id=identity.user_id,
        organization_id=identity.organization_id,
        resource_type="session",
        resource_id=identity.session_id,
    )
    return {"status": "logged_out"}


@router.get("/me")
def me(identity: Identity = Depends(get_identity)) -> dict[str, str]:
    return {
        "user_id": str(identity.user_id),
        "role": identity.role.value,
        "organization_id": str(identity.organization_id),
    }
