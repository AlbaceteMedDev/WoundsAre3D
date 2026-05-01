"""Admin endpoints: products, audit log, ML metrics."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from woundscan.api.auth import get_identity
from woundscan.auth.identity import Identity, Role
from woundscan.auth.rbac import Permission, has_permission
from woundscan.graft.product_db import default_product_db

router = APIRouter(prefix="/admin", tags=["admin"])

_PRODUCT_DB = default_product_db()


def _require(permission: Permission, identity: Identity) -> None:
    if not has_permission(identity.role, permission):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


@router.get("/products")
def list_products(identity: Identity = Depends(get_identity)) -> dict:
    return {
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "manufacturer": p.manufacturer,
                "overlap_delta_cm": p.overlap_delta_cm,
                "available_sizes_cm2": list(p.available_sizes_cm2),
                "indications": list(p.indications),
            }
            for p in _PRODUCT_DB.products.values()
        ]
    }


@router.get("/audit")
def list_audit(identity: Identity = Depends(get_identity)) -> dict:
    _require(Permission.READ_AUDIT_LOG, identity)
    from woundscan.api.audit import get_audit_logger

    logger = get_audit_logger()
    return {"entries": logger.entries[-200:], "total": len(logger.entries)}


@router.get("/ml-metrics")
def ml_metrics(identity: Identity = Depends(get_identity)) -> dict:
    _require(Permission.READ_ML_METRICS, identity)
    return {
        "boundary_iou_mean": None,
        "tissue_macro_f1": None,
        "probe_detection_recall": None,
        "drift_alerts": [],
        "note": "Backend wired in production deployment",
    }
