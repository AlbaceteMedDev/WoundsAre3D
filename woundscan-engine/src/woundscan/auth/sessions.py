"""Sessions, JWTs, idle timeout."""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

SESSION_TIMEOUT_MINUTES = 15


@dataclass
class Session:
    """An active server-side session.

    JWTs are short-lived (15-min idle) and refreshed by re-issuance on
    activity. The session_id is stored in Redis with a TTL equal to the
    idle timeout. Logout deletes the Redis entry which immediately
    invalidates the JWT.
    """

    session_id: str
    user_id: UUID
    role: str
    organization_id: UUID
    created_at: datetime
    last_activity_at: datetime
    expires_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionStore:
    """In-memory session store. Production deployments use Redis."""

    sessions: dict[str, Session] = field(default_factory=dict)

    def put(self, session: Session) -> None:
        self.sessions[session.session_id] = session

    def get(self, session_id: str) -> Session | None:
        s = self.sessions.get(session_id)
        if s is None:
            return None
        if s.expires_at < datetime.now(UTC):
            self.sessions.pop(session_id, None)
            return None
        return s

    def delete(self, session_id: str) -> None:
        self.sessions.pop(session_id, None)

    def touch(self, session_id: str) -> None:
        s = self.get(session_id)
        if s is None:
            return
        now = datetime.now(UTC)
        s.last_activity_at = now
        s.expires_at = now + timedelta(minutes=SESSION_TIMEOUT_MINUTES)


def create_session(user_id: UUID, role: str, organization_id: UUID) -> Session:
    now = datetime.now(UTC)
    return Session(
        session_id=secrets.token_urlsafe(32),
        user_id=user_id,
        role=role,
        organization_id=organization_id,
        created_at=now,
        last_activity_at=now,
        expires_at=now + timedelta(minutes=SESSION_TIMEOUT_MINUTES),
    )


def issue_jwt(session: Session, signing_key: str) -> str:
    """Issue a JWT bound to a server-side session."""
    from jose import jwt

    payload = {
        "sid": session.session_id,
        "sub": str(session.user_id),
        "role": session.role,
        "org": str(session.organization_id),
        "iat": int(session.created_at.timestamp()),
        "exp": int(session.expires_at.timestamp()),
    }
    return jwt.encode(payload, signing_key, algorithm="HS256")


def verify_jwt(token: str, signing_key: str) -> dict[str, Any] | None:
    """Verify and decode a JWT. Returns claims dict or None if invalid."""
    from jose import jwt
    from jose.exceptions import JWTError

    try:
        return jwt.decode(token, signing_key, algorithms=["HS256"])
    except JWTError:
        return None
