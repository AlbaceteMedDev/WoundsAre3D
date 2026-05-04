"""Synthesis: synthetic wound generators for validation and ML training."""

from __future__ import annotations

from woundscan.synthesis.analytic_shapes import (
    AnalyticWound,
    cone,
    flat_disk,
    hemisphere,
    hemispheroid,
    paraboloid,
)
from woundscan.synthesis.clinical_morphologies import (
    diabetic_foot_ulcer,
    pressure_injury_stage_3,
    pressure_injury_stage_4,
    surgical_dehiscence,
    traumatic_wound,
    venous_leg_ulcer,
)
from woundscan.synthesis.degradation import (
    DegradationConfig,
    add_lighting_variation,
    add_motion_artifact,
    add_sensor_noise,
    add_specular_highlights,
    degrade_synthetic_wound,
)
from woundscan.synthesis.ground_truth import GroundTruth, compute_ground_truth
from woundscan.synthesis.irregular_beds import (
    IrregularConfig,
    add_perlin_noise,
    irregular_paraboloid,
)

__all__ = [
    "AnalyticWound",
    "DegradationConfig",
    "GroundTruth",
    "IrregularConfig",
    "add_lighting_variation",
    "add_motion_artifact",
    "add_perlin_noise",
    "add_sensor_noise",
    "add_specular_highlights",
    "compute_ground_truth",
    "cone",
    "degrade_synthetic_wound",
    "diabetic_foot_ulcer",
    "flat_disk",
    "hemisphere",
    "hemispheroid",
    "irregular_paraboloid",
    "paraboloid",
    "pressure_injury_stage_3",
    "pressure_injury_stage_4",
    "surgical_dehiscence",
    "traumatic_wound",
    "venous_leg_ulcer",
]
