"""Measurement endpoints: create, get, list, sign-off, exports."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from woundscan.api.audit import get_audit_logger
from woundscan.api.auth import get_identity
from woundscan.api.models.measurement import (
    CreateMeasurementRequest,
    MeasurementResponse,
)
from woundscan.api.pipeline import PipelineDependencies, run_measurement_pipeline
from woundscan.auth.audit_log import AuditAction, AuditLogger
from woundscan.auth.identity import Identity
from woundscan.graft.product_db import default_product_db

router = APIRouter(prefix="/measurements", tags=["measurements"])

_DEFAULT_PRODUCT_DB = default_product_db()
_DEFAULT_DEPS = PipelineDependencies(product_db=_DEFAULT_PRODUCT_DB)

_RESPONSE_CACHE: dict[UUID, MeasurementResponse] = {}


@router.post("", response_model=MeasurementResponse, status_code=status.HTTP_201_CREATED)
def create_measurement(
    request: CreateMeasurementRequest,
    identity: Identity = Depends(get_identity),
    audit: AuditLogger = Depends(get_audit_logger),
) -> MeasurementResponse:
    """Run the engine pipeline on the supplied capture data."""
    response = run_measurement_pipeline(request, _DEFAULT_DEPS)
    _RESPONSE_CACHE[response.measurement_id] = response
    audit.log(
        action=AuditAction.CREATE_MEASUREMENT,
        user_id=identity.user_id,
        organization_id=identity.organization_id,
        resource_type="measurement",
        resource_id=str(response.measurement_id),
        metadata={
            "wound_id": str(request.wound_id),
            "quality_grade": response.quality.grade,
            "duration_ms": response.processing_duration_ms,
        },
    )
    return response


@router.get("/{measurement_id}", response_model=MeasurementResponse)
def get_measurement(
    measurement_id: UUID,
    identity: Identity = Depends(get_identity),
    audit: AuditLogger = Depends(get_audit_logger),
) -> MeasurementResponse:
    if measurement_id not in _RESPONSE_CACHE:
        raise HTTPException(status_code=404, detail="Measurement not found")
    audit.log(
        action=AuditAction.READ_MEASUREMENT,
        user_id=identity.user_id,
        organization_id=identity.organization_id,
        resource_type="measurement",
        resource_id=str(measurement_id),
    )
    return _RESPONSE_CACHE[measurement_id]


@router.post("/{measurement_id}/sign-off")
def sign_off_measurement(
    measurement_id: UUID,
    identity: Identity = Depends(get_identity),
    audit: AuditLogger = Depends(get_audit_logger),
) -> dict[str, str]:
    if measurement_id not in _RESPONSE_CACHE:
        raise HTTPException(status_code=404, detail="Measurement not found")
    audit.log(
        action=AuditAction.SIGN_OFF_MEASUREMENT,
        user_id=identity.user_id,
        organization_id=identity.organization_id,
        resource_type="measurement",
        resource_id=str(measurement_id),
        metadata={"signed_off_at": datetime.now(timezone.utc).isoformat()},
    )
    return {"status": "signed_off"}


@router.get("/{measurement_id}/pdf", responses={200: {"content": {"application/pdf": {}}}})
def get_measurement_pdf(
    measurement_id: UUID,
    identity: Identity = Depends(get_identity),
    audit: AuditLogger = Depends(get_audit_logger),
) -> Response:
    if measurement_id not in _RESPONSE_CACHE:
        raise HTTPException(status_code=404, detail="Measurement not found")
    response = _RESPONSE_CACHE[measurement_id]
    pdf_bytes = _render_pdf_for(response)
    audit.log(
        action=AuditAction.EXPORT_PDF,
        user_id=identity.user_id,
        organization_id=identity.organization_id,
        resource_type="measurement",
        resource_id=str(measurement_id),
    )
    return Response(content=pdf_bytes, media_type="application/pdf")


@router.get("/{measurement_id}/fhir")
def get_measurement_fhir(
    measurement_id: UUID,
    identity: Identity = Depends(get_identity),
    audit: AuditLogger = Depends(get_audit_logger),
) -> dict:
    from woundscan.output.fhir_export import build_fhir_observation_bundle

    if measurement_id not in _RESPONSE_CACHE:
        raise HTTPException(status_code=404, detail="Measurement not found")
    r = _RESPONSE_CACHE[measurement_id]
    bundle = build_fhir_observation_bundle(
        patient_token="opaque",
        measurement_id=str(measurement_id),
        captured_at=r.captured_at,
        volume_cm3=r.volume.mean,
        volume_ci_low=r.volume.ci_95_low,
        volume_ci_high=r.volume.ci_95_high,
        surface_area_cm2=r.surface_area.mean,
        surface_area_ci_low=r.surface_area.ci_95_low,
        surface_area_ci_high=r.surface_area.ci_95_high,
        max_depth_cm=r.max_depth_cm,
    )
    audit.log(
        action=AuditAction.EXPORT_FHIR,
        user_id=identity.user_id,
        organization_id=identity.organization_id,
        resource_type="measurement",
        resource_id=str(measurement_id),
    )
    return bundle


def _render_pdf_for(response: MeasurementResponse) -> bytes:
    from woundscan.output.pdf_report import ReportData, build_pdf_report

    data = ReportData(
        measurement_id=str(response.measurement_id),
        patient_token="opaque",
        wound_id=str(response.wound_id),
        captured_at=response.captured_at.isoformat(),
        clinician_id="dev",
        volume_cm3=response.volume.mean,
        volume_ci_low=response.volume.ci_95_low,
        volume_ci_high=response.volume.ci_95_high,
        surface_area_cm2=response.surface_area.mean,
        surface_area_ci_low=response.surface_area.ci_95_low,
        surface_area_ci_high=response.surface_area.ci_95_high,
        max_depth_cm=response.max_depth_cm,
        mean_depth_cm=response.mean_depth_cm,
        quality_grade=response.quality.grade,
        quality_components=response.quality.components,
        graft_recommendations=[r.model_dump() for r in response.graft_recommendations],
        methodology_notes=(
            "Volume = double Simpson integral of fused depth field. "
            "3D surface area = gradient integral. "
            "Fusion = heteroscedastic Gaussian process over probe + camera anchors. "
            "Uncertainty = Monte Carlo sampling from posterior. "
            "Graft size = mean + 2 sigma upper bound, IFU overlap applied."
        ),
        provenance_json=str(response.provenance),
    )
    return build_pdf_report(data)
