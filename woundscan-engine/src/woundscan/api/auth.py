"""FastAPI auth dependency: extract identity from JWT bearer."""
from __future__ import annotations

import os
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from woundscan.auth.identity import Identity, Role
from woundscan.auth.sessions import verify_jwt

_security = HTTPBearer(auto_error=False)


def _signing_key() -> str:
    key = os.environ.get("WS_JWT_SIGNING_KEY")
    if not key:
        # Insecure default for local dev only; production deployments
        # MUST set WS_JWT_SIGNING_KEY via Secrets Manager.
        return "INSECURE_DEV_KEY_DO_NOT_USE_IN_PRODUCTION"
    return key


def get_identity(
    creds: HTTPAuthorizationCredentials | None = Depends(_security),
) -> Identity:
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token"
        )
    claims = verify_jwt(creds.credentials, _signing_key())
    if claims is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )
    try:
        return Identity(
            user_id=UUID(claims["sub"]),
            email=claims.get("email", ""),
            role=Role(claims["role"]),
            organization_id=UUID(claims["org"]),
            session_id=claims["sid"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Malformed token: {e}"
        ) from e
