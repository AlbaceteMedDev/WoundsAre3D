"""Tests for auth: passwords, MFA, sessions, RBAC."""
import pytest

from woundscan.auth.audit_log import AuditAction, AuditLogger
from woundscan.auth.identity import Role, hash_password, verify_password
from woundscan.auth.mfa import (
    generate_recovery_codes,
    generate_totp_secret,
    verify_totp_code,
)
from woundscan.auth.rbac import Permission, has_permission
from woundscan.auth.sessions import (
    SessionStore,
    create_session,
    issue_jwt,
    verify_jwt,
)
from uuid import uuid4


class TestPasswords:
    def test_hash_verify(self):
        h = hash_password("hunter2")
        assert verify_password("hunter2", h)
        assert not verify_password("wrong", h)


class TestTOTP:
    def test_generate_and_verify(self):
        import pyotp

        secret = generate_totp_secret()
        code = pyotp.TOTP(secret).now()
        assert verify_totp_code(secret, code)

    def test_wrong_code_fails(self):
        secret = generate_totp_secret()
        assert not verify_totp_code(secret, "000000")

    def test_recovery_codes_unique(self):
        codes = generate_recovery_codes(8)
        assert len(set(codes)) == 8


class TestSessions:
    def test_create_and_verify_jwt(self):
        s = create_session(uuid4(), Role.CLINICIAN.value, uuid4())
        token = issue_jwt(s, "test-key")
        claims = verify_jwt(token, "test-key")
        assert claims is not None
        assert claims["sub"] == str(s.user_id)
        assert claims["role"] == s.role

    def test_wrong_key_fails(self):
        s = create_session(uuid4(), Role.CLINICIAN.value, uuid4())
        token = issue_jwt(s, "key-a")
        assert verify_jwt(token, "key-b") is None

    def test_session_store_get_delete(self):
        store = SessionStore()
        s = create_session(uuid4(), Role.CLINICIAN.value, uuid4())
        store.put(s)
        assert store.get(s.session_id) is not None
        store.delete(s.session_id)
        assert store.get(s.session_id) is None


class TestRBAC:
    def test_clinician_can_create_measurement(self):
        assert has_permission(Role.CLINICIAN, Permission.CREATE_MEASUREMENT)

    def test_clinician_cannot_read_audit(self):
        assert not has_permission(Role.CLINICIAN, Permission.READ_AUDIT_LOG)

    def test_admin_can_read_audit(self):
        assert has_permission(Role.ADMIN, Permission.READ_AUDIT_LOG)


class TestAuditLog:
    def test_log_appends_chain(self):
        logger = AuditLogger()
        e1 = logger.log(AuditAction.LOGIN, uuid4(), uuid4(), "session", "abc")
        e2 = logger.log(AuditAction.READ_MEASUREMENT, uuid4(), uuid4(), "measurement", "m1")
        assert e1["chain_self_hash"] != e2["chain_self_hash"]
        assert logger.sequence == 2
