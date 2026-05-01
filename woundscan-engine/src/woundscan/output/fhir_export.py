"""FHIR R4 Observation bundle export.

Builds a FHIR Bundle of Observations: one for volume, one for surface
area, one for depth. Suitable for ingestion by an EHR via FHIR API. We
do NOT push directly; we expose a download endpoint and let the
deployment partner do their own integration.

Only includes the Observation resources; Patient and Encounter
references are placeholders the integration partner fills in.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any


def _observation(
    code: str,
    display: str,
    value: float,
    unit: str,
    patient_token: str,
    measurement_id: str,
    captured_at: datetime,
    low: float | None = None,
    high: float | None = None,
) -> dict[str, Any]:
    obs: dict[str, Any] = {
        "resourceType": "Observation",
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "exam",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": code,
                    "display": display,
                }
            ]
        },
        "subject": {"reference": f"Patient/{patient_token}"},
        "effectiveDateTime": captured_at.isoformat(),
        "valueQuantity": {
            "value": float(value),
            "unit": unit,
            "system": "http://unitsofmeasure.org",
            "code": unit,
        },
        "identifier": [{"value": measurement_id}],
    }
    if low is not None and high is not None:
        obs["referenceRange"] = [
            {
                "low": {"value": float(low), "unit": unit},
                "high": {"value": float(high), "unit": unit},
                "type": {"text": "95% confidence interval"},
            }
        ]
    return obs


def build_fhir_observation_bundle(
    *,
    patient_token: str,
    measurement_id: str,
    captured_at: datetime,
    volume_cm3: float,
    volume_ci_low: float,
    volume_ci_high: float,
    surface_area_cm2: float,
    surface_area_ci_low: float,
    surface_area_ci_high: float,
    max_depth_cm: float,
) -> dict[str, Any]:
    """Build a FHIR Bundle dict ready to serialize to JSON."""
    obs_v = _observation(
        "89261-2",
        "Wound volume",
        volume_cm3,
        "cm3",
        patient_token,
        measurement_id,
        captured_at,
        volume_ci_low,
        volume_ci_high,
    )
    obs_sa = _observation(
        "89262-0",
        "Wound 3D surface area",
        surface_area_cm2,
        "cm2",
        patient_token,
        measurement_id,
        captured_at,
        surface_area_ci_low,
        surface_area_ci_high,
    )
    obs_d = _observation(
        "39125-0",
        "Wound maximum depth",
        max_depth_cm,
        "cm",
        patient_token,
        measurement_id,
        captured_at,
    )
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [{"resource": obs_v}, {"resource": obs_sa}, {"resource": obs_d}],
    }
