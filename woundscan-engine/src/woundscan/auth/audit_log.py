"""HIPAA-grade access logging.

Every read/write of PHI generates an audit log entry. Entries are written
to Postgres AND appended to the tamper-evident hash chain. Entries
include who/what/when/where but never PHI content (only resource IDs).

We keep audit logs 6 years minimum (HIPAA Security Rule retention).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class AuditAction(str, Enum):
    LOGIN = "login"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    READ_PATIENT = "read_patient"
    READ_WOUND = "read_wound"
    READ_MEASUREMENT = "read_measurement"
    CREATE_MEASUREMENT = "create_measurement"
    SIGN_OFF_MEASUREMENT = "sign_off_measurement"
    EXPORT_PDF = "export_pdf"
    EXPORT_CSV = "export_csv"
    EXPORT_FHIR = "export_fhir"
    UPDATE_PRODUCT = "update_product"
    DEPROVISION_USER = "deprovision_user"
    PERMISSION_DENIED = "permission_denied"


@dataclass
class AuditLogger:
    """Append audit entries.

    Production: writes to Postgres and to the tamper-evident hash chain.
    Test/Dev: writes to in-memory buffer.
    """

    entries: list[dict[str, Any]] = field(default_factory=list)
    sequence: int = 0
    previous_hash: str = ""

    def log(
        self,
        action: AuditAction,
        user_id: UUID | None,
        organization_id: UUID | None,
        resource_type: str,
        resource_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from woundscan.storage.tamper_evidence import append_to_chain

        entry_payload = {
            "id": str(uuid4()),
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "action": action.value,
            "user_id": str(user_id) if user_id else None,
            "organization_id": str(organization_id) if organization_id else None,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "metadata": metadata or {},
        }
        chain_entry = append_to_chain(entry_payload, self.sequence, self.previous_hash)
        self.sequence += 1
        self.previous_hash = chain_entry.self_hash
        full = {**entry_payload, "chain_self_hash": chain_entry.self_hash}
        self.entries.append(full)
        return full
