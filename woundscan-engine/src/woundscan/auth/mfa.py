"""TOTP-based multi-factor authentication."""
from __future__ import annotations

import secrets


def generate_totp_secret() -> str:
    """Generate a base32-encoded TOTP secret."""
    import pyotp

    return pyotp.random_base32(length=32)


def verify_totp_code(secret_b32: str, code: str, valid_window: int = 1) -> bool:
    """Verify a 6-digit TOTP code against the secret. Default 30s window +- 1."""
    import pyotp

    if not code.isdigit() or len(code) not in (6, 8):
        return False
    totp = pyotp.TOTP(secret_b32)
    return totp.verify(code, valid_window=valid_window)


def generate_recovery_codes(n: int = 8) -> list[str]:
    """Generate human-readable recovery codes (8 by default).

    Each code is 12 hex characters in groups of 4.
    """
    out = []
    for _ in range(n):
        raw = secrets.token_hex(6)
        formatted = f"{raw[:4]}-{raw[4:8]}-{raw[8:12]}"
        out.append(formatted)
    return out
