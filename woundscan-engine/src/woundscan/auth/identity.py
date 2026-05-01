"""User identity, password hashing."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class Role(str, Enum):
    CLINICIAN = "clinician"
    REVIEWER = "reviewer"
    ADMIN = "admin"


@dataclass(frozen=True)
class User:
    """A registered user. Stored row in `users` table."""

    id: UUID
    email: str
    role: Role
    organization_id: UUID
    password_hash: str
    totp_secret_encrypted: str | None
    is_active: bool
    last_login_at: str | None


@dataclass(frozen=True)
class Identity:
    """Authenticated identity: who is making this request."""

    user_id: UUID
    email: str
    role: Role
    organization_id: UUID
    session_id: str


def hash_password(plain: str) -> str:
    """Hash a password using bcrypt with auto-generated salt."""
    from passlib.hash import bcrypt

    return bcrypt.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    from passlib.hash import bcrypt

    try:
        return bcrypt.verify(plain, hashed)
    except Exception:
        return False
