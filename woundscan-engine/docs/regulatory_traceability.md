# Regulatory Traceability Matrix

Bidirectional mapping: every requirement → at least one test, every test
→ at least one requirement. Failure of any traced test is a regulatory
deviation that must be logged and investigated.

| Req ID | Description | Implementation | Test |
|---|---|---|---|
| REQ-ACC-001 | Hemisphere volume <2% | `geometry.volume.compute_volume` | `tests/regulatory/test_synthetic_accuracy.py::test_REQ_ACC_001_hemisphere_volume` |
| REQ-ACC-002 | Cone volume <1% and SA <3% | `geometry.volume.compute_volume`, `geometry.surface_area.compute_surface_area` | `tests/regulatory/test_synthetic_accuracy.py::test_REQ_ACC_002_cone_volume_and_sa` |
| REQ-ACC-003 | Paraboloid volume <1% and SA <5% | same | `tests/regulatory/test_synthetic_accuracy.py::test_REQ_ACC_003_paraboloid_volume_and_sa` |
| REQ-ACC-004 | Oblate hemispheroid (wide) <2%/<5% | same | `tests/regulatory/test_synthetic_accuracy.py::test_REQ_ACC_004_oblate_hemispheroid_wide` |
| REQ-ACC-005 | Irregular bed (Perlin) <1% vs numerical truth | same + `synthesis.irregular_beds` | `tests/regulatory/test_synthetic_accuracy.py::test_REQ_ACC_005_irregular_paraboloid` |
| REQ-ACC-006 | Grid-independence; refinement reduces error | `geometry.volume.compute_volume` | `tests/regulatory/test_synthetic_accuracy.py::test_REQ_ACC_006_grid_independence` |
| REQ-INV-001 | Volume scale equivariance | `geometry.volume.compute_volume` | `tests/regulatory/test_property_invariants.py::TestInvariants::test_volume_scale_equivariance` |
| REQ-INV-002 | Surface area scale equivariance | `geometry.surface_area.compute_surface_area` | `tests/regulatory/test_property_invariants.py::TestInvariants::test_surface_area_scale_equivariance` |
| REQ-INV-003 | Volume monotonicity in depth | `geometry.volume.compute_volume` | `tests/regulatory/test_property_invariants.py::TestInvariants::test_volume_monotonicity` |
| REQ-INV-004 | Volume translation invariance | `geometry.volume.compute_volume` | `tests/regulatory/test_property_invariants.py::TestInvariants::test_volume_translation_invariance` |
| REQ-INV-005 | 95% CI contains truth (low noise) | `geometry.uncertainty.compute_volume_with_uncertainty` | `tests/regulatory/test_property_invariants.py::TestUncertaintyCalibration::test_volume_ci_contains_truth_when_noise_is_small` |
| REQ-FUS-001 | GP fuses to anchor depths | `fusion.gaussian_process.fuse_gaussian_process` | `tests/unit/test_fusion.py::TestGPFusion::test_fuses_to_probe_anchors` |
| REQ-FUS-002 | TPS interpolates exactly through anchors | `fusion.interpolation.thin_plate_spline` | `tests/unit/test_fusion.py::TestThinPlateSpline::test_interpolates_through_anchors` |
| REQ-FUS-003 | Force correction reduces depth | `fusion.force_correction.apply_force_correction` | `tests/unit/test_fusion.py::TestForceCorrection::test_correction_reduces_depth` |
| REQ-FUS-004 | Kalman pulls toward observation | `fusion.temporal.kalman_update` | `tests/unit/test_fusion.py::TestTemporalKalman::test_update_pulls_toward_observation` |
| REQ-FUS-005 | Kalman flags outliers | `fusion.temporal.kalman_update` | `tests/unit/test_fusion.py::TestTemporalKalman::test_outlier_flagged` |
| REQ-Q-001 | Confidence weights sum to 1 | `quality.confidence.ConfidenceWeights` | `tests/unit/test_quality.py::TestConfidenceMap::test_weights_must_sum_to_one` |
| REQ-Q-002 | Default confidence weights valid | same | `tests/unit/test_quality.py::TestConfidenceMap::test_default_weights_valid` |
| REQ-Q-003 | Specularity high on white pixels | `quality.specularity.compute_specularity` | `tests/unit/test_quality.py::TestSpecularity::test_white_pixels_are_specular` |
| REQ-Q-004 | Frame consistency high on stable frames | `quality.frame_consistency.compute_frame_consistency` | `tests/unit/test_quality.py::TestFrameConsistency::test_identical_frames_score_one` |
| REQ-VAL-001 | Plausibility rejects negative volume | `validation.plausibility` | `tests/unit/test_validation.py::TestPlausibility::test_negative_volume_fails` |
| REQ-VAL-002 | Quality grade A on perfect inputs | `validation.quality_score.compute_quality_grade` | `tests/unit/test_validation.py::TestQualityGrade::test_a_grade_perfect_inputs` |
| REQ-VAL-003 | Quality grade F on terrible inputs | same | `tests/unit/test_validation.py::TestQualityGrade::test_f_grade_terrible_inputs` |
| REQ-VAL-004 | Camera-probe disagreement flagged | `validation.consistency.check_camera_probe_agreement` | `tests/unit/test_validation.py::TestConsistency::test_disagreement_fails` |
| REQ-VAL-005 | Phantom drift alert | `validation.phantom_calibration.PhantomCalibration` | `tests/unit/test_validation.py::TestPhantomCalibration::test_drift_alert` |
| REQ-VAL-006 | Temporal implausibility flagged | `validation.temporal_plausibility` | `tests/unit/test_validation.py::TestTemporalPlausibility::test_implausible_change_flagged` |
| REQ-GFT-001 | Graft size > point estimate (under uncertainty) | `graft.sizing.compute_graft_size` | `tests/unit/test_graft.py::TestGraftSizing::test_recommendation_above_point_estimate` |
| REQ-GFT-002 | Overlap delta increases graft size | same | `tests/unit/test_graft.py::TestGraftSizing::test_overlap_increases_size` |
| REQ-GFT-003 | Recommendations filtered by indication | `graft.recommendation.recommend_grafts` | `tests/unit/test_graft.py::TestRecommendation::test_recommends_for_indication` |
| REQ-GFT-004 | Contraindications exclude products | same | `tests/unit/test_graft.py::TestRecommendation::test_contraindication_excludes_product` |
| REQ-OUT-001 | Provenance hash deterministic | `output.provenance.hash_array` | `tests/unit/test_output.py::TestProvenance::test_hash_array_deterministic` |
| REQ-OUT-002 | FHIR bundle has 3 observations | `output.fhir_export.build_fhir_observation_bundle` | `tests/unit/test_output.py::TestFHIR::test_bundle_has_three_observations` |
| REQ-STO-001 | Hash chain detects tampering | `storage.tamper_evidence.verify_chain` | `tests/unit/test_storage.py::TestHashChain::test_tampered_payload_fails` |
| REQ-STO-002 | Hash chain detects skipped sequences | same | `tests/unit/test_storage.py::TestHashChain::test_skipped_sequence_fails` |
| REQ-AUTH-001 | Password hash + verify | `auth.identity.hash_password` | `tests/unit/test_auth.py::TestPasswords::test_hash_verify` |
| REQ-AUTH-002 | TOTP verify | `auth.mfa.verify_totp_code` | `tests/unit/test_auth.py::TestTOTP::test_generate_and_verify` |
| REQ-AUTH-003 | JWT round-trip | `auth.sessions.issue_jwt`, `verify_jwt` | `tests/unit/test_auth.py::TestSessions::test_create_and_verify_jwt` |
| REQ-AUTH-004 | RBAC denies unauthorized | `auth.rbac.has_permission` | `tests/unit/test_auth.py::TestRBAC::test_clinician_cannot_read_audit` |
| REQ-AUTH-005 | Audit chain links | `auth.audit_log.AuditLogger` | `tests/unit/test_auth.py::TestAuditLog::test_log_appends_chain` |
| REQ-CAP-001 | LiDAR depth in cm after load | `capture.depth_map.load_depth_frame` | `tests/unit/test_capture.py::TestDepthFrame::test_load_converts_meters_to_cm` |
| REQ-CAP-002 | Multi-frame averaging reduces noise | `capture.multiframe.temporal_average_depth` | `tests/unit/test_capture.py::TestMultiframe::test_temporal_average_reduces_noise` |
| REQ-CAP-003 | Polarization decomposition | `capture.polarization.extract_diffuse_specular` | `tests/unit/test_capture.py::TestPolarization::test_diffuse_specular_decomposition` |
| REQ-API-001 | Healthz responds 200 | `api.routes.health` | `tests/integration/test_api.py::TestHealth::test_healthz` |
| REQ-API-002 | Auth required for protected endpoints | `api.auth.get_identity` | `tests/integration/test_api.py::TestAuth::test_me_requires_token` |
| REQ-API-003 | Login returns valid JWT | `api.routes.auth` | `tests/integration/test_api.py::TestAuth::test_me_with_token` |
| REQ-PIPE-001 | Pipeline produces measurement | `api.pipeline.run_measurement_pipeline` | `tests/integration/test_pipeline.py::TestPipeline::test_pipeline_produces_response` |
| REQ-PIPE-002 | Pipeline F-grade with no anchors | same | `tests/integration/test_pipeline.py::TestPipeline::test_pipeline_handles_no_probe` |
| REQ-PIPE-003 | Provenance has all required fields | same | `tests/integration/test_pipeline.py::TestPipeline::test_pipeline_provenance_has_all_fields` |

## Coverage check

Run `python scripts/check_traceability.py` to verify every test in the
suite is referenced here and every requirement is mapped to a test.
