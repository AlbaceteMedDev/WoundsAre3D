"""Role-based access control.

Roles -> Permissions matrix. Checked in API route dependencies and at the
Postgres row-level security policies (defense in depth).
"""

from __future__ import annotations

from enum import StrEnum

from woundscan.auth.identity import Role


class Permission(StrEnum):
    READ_OWN_PATIENTS = "read_own_patients"
    READ_ORG_PATIENTS = "read_org_patients"
    READ_ALL_PATIENTS = "read_all_patients"
    CREATE_MEASUREMENT = "create_measurement"
    SIGN_OFF_MEASUREMENT = "sign_off_measurement"
    EXPORT_PHI = "export_phi"
    READ_AUDIT_LOG = "read_audit_log"
    MANAGE_PRODUCTS = "manage_products"
    MANAGE_USERS = "manage_users"
    READ_ML_METRICS = "read_ml_metrics"


_ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.CLINICIAN: {
        Permission.READ_OWN_PATIENTS,
        Permission.CREATE_MEASUREMENT,
        Permission.SIGN_OFF_MEASUREMENT,
    },
    Role.REVIEWER: {
        Permission.READ_OWN_PATIENTS,
        Permission.READ_ORG_PATIENTS,
        Permission.SIGN_OFF_MEASUREMENT,
    },
    Role.ADMIN: {
        Permission.READ_OWN_PATIENTS,
        Permission.READ_ORG_PATIENTS,
        Permission.READ_ALL_PATIENTS,
        Permission.READ_AUDIT_LOG,
        Permission.MANAGE_PRODUCTS,
        Permission.MANAGE_USERS,
        Permission.READ_ML_METRICS,
        Permission.EXPORT_PHI,
    },
}


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in _ROLE_PERMISSIONS.get(role, set())
