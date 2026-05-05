/**
 * API client for the WoundScan engine.
 *
 * Uses fetch + cookies; the JWT lives in an HTTP-only cookie set by the
 * Next.js auth route, never exposed to client JS. Requests are made via
 * Next.js server-side fetch when possible.
 */
import { z } from "zod";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class APIError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "APIError";
  }
}

export async function apiFetch<T>(path: string, init: RequestInit & { schema: z.ZodSchema<T>; token?: string }): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (init.token) headers.set("Authorization", `Bearer ${init.token}`);
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  const text = await res.text();
  if (!res.ok) {
    throw new APIError(res.status, text);
  }
  const json = text ? JSON.parse(text) : {};
  return init.schema.parse(json);
}

export const UncertaintySchema = z.object({
  mean: z.number(),
  std: z.number(),
  ci_95_low: z.number(),
  ci_95_high: z.number(),
});

export const QualitySchema = z.object({
  grade: z.string(),
  overall_score: z.number(),
  components: z.record(z.string(), z.number()),
  recommendation: z.string(),
});

export const GraftRecommendationSchema = z.object({
  product_id: z.string(),
  product_name: z.string(),
  overlap_delta_cm: z.number(),
  required_cm2: z.number(),
  selected_size_cm2: z.number().nullable(),
  rationale: z.string(),
});

export const MeasurementSchema = z.object({
  measurement_id: z.string(),
  wound_id: z.string(),
  captured_at: z.string(),
  processed_at: z.string(),
  processing_duration_ms: z.number(),
  volume: UncertaintySchema,
  surface_area: UncertaintySchema,
  max_depth_cm: z.number(),
  mean_depth_cm: z.number(),
  perimeter_cm: z.number(),
  footprint_area_cm2: z.number(),
  quality: QualitySchema,
  graft_recommendations: z.array(GraftRecommendationSchema),
  plausibility_passed: z.boolean(),
  plausibility_warnings: z.array(z.string()),
  temporal_warnings: z.array(z.string()),
  pdf_s3_key: z.string(),
  provenance: z.record(z.string(), z.unknown()),
});

export type Measurement = z.infer<typeof MeasurementSchema>;

export const ProgressionPointSchema = z.object({
  measurement_id: z.string(),
  captured_at: z.string(),
  volume_cm3: z.number(),
  surface_area_cm2: z.number(),
  max_depth_cm: z.number(),
  mean_depth_cm: z.number(),
  perimeter_cm: z.number(),
  quality_grade: z.string(),
});

export const ProgressionTrendSchema = z.object({
  first_capture_at: z.string().nullable(),
  last_capture_at: z.string().nullable(),
  days_observed: z.number(),
  initial_area_cm2: z.number().nullable(),
  latest_area_cm2: z.number().nullable(),
  pct_area_change: z.number().nullable(),
  initial_volume_cm3: z.number().nullable(),
  latest_volume_cm3: z.number().nullable(),
  pct_volume_change: z.number().nullable(),
  healing_rate_cm2_per_week: z.number().nullable(),
  is_healing: z.boolean(),
  is_stalled: z.boolean(),
});

export const ProgressionResponseSchema = z.object({
  wound_id: z.string(),
  points: z.array(ProgressionPointSchema),
  trend: ProgressionTrendSchema,
});

export type ProgressionPoint = z.infer<typeof ProgressionPointSchema>;
export type ProgressionTrend = z.infer<typeof ProgressionTrendSchema>;
export type ProgressionResponse = z.infer<typeof ProgressionResponseSchema>;

export const GraftApplicationSchema = z.object({
  id: z.string(),
  wound_id: z.string(),
  measurement_id: z.string().nullable(),
  organization_id: z.string(),
  applied_by: z.string(),
  applied_at: z.string(),
  product_id: z.string(),
  product_name: z.string(),
  udi_di: z.string().nullable(),
  serial_number: z.string(),
  lot_number: z.string(),
  expiration_date: z.string(),
  manufacture_date: z.string().nullable(),
  package_size_cm2: z.number(),
  applied_area_cm2: z.number(),
  waste_area_cm2: z.number(),
  hcpcs_code: z.string().nullable(),
  cpt_code: z.string().nullable(),
  notes: z.string(),
});
export const GraftApplicationListSchema = z.array(GraftApplicationSchema);
export type GraftApplication = z.infer<typeof GraftApplicationSchema>;

export const ReimbursementOutSchema = z.object({
  pos: z.string(),
  primary_cpt: z.string(),
  additional_cpt_units: z.number(),
  primary_cpt_payment: z.number(),
  additional_units_payment: z.number(),
  drug_payment: z.number(),
  total_payment: z.number(),
  breakdown: z.record(z.string(), z.unknown()),
  notes: z.array(z.string()),
});
export type ReimbursementOut = z.infer<typeof ReimbursementOutSchema>;

export const NoteOutSchema = z.object({
  id: z.string(),
  wound_id: z.string(),
  measurement_id: z.string(),
  organization_id: z.string(),
  authored_by: z.string(),
  authored_at: z.string(),
  template_version: z.string(),
  body_text: z.string(),
  body_sha256: z.string(),
  is_signed: z.boolean(),
  signed_at: z.string().nullable(),
  metadata: z.record(z.string(), z.unknown()),
});
export const NoteListSchema = z.array(NoteOutSchema);
export type NoteOut = z.infer<typeof NoteOutSchema>;

export const ANATOMIC_REGIONS = [
  { value: "trunk_arms_legs", label: "Trunk / arms / legs", cpts: "15271 / 15272" },
  { value: "face_scalp_digits", label: "Face / scalp / digits", cpts: "15275 / 15276" },
] as const;

export const PLACE_OF_SERVICE = [
  { code: "11", label: "Office (non-facility)" },
  { code: "22", label: "Hospital outpatient (facility)" },
  { code: "23", label: "Emergency dept (facility)" },
  { code: "31", label: "Skilled nursing facility" },
  { code: "12", label: "Home" },
  { code: "20", label: "Urgent care" },
] as const;

export const WOUND_TYPES = [
  "diabetic_foot_ulcer",
  "venous_leg_ulcer",
  "arterial_ulcer",
  "pressure_injury",
  "surgical_dehiscence",
  "trauma",
  "burn",
  "other",
] as const;

export const TISSUE_CHANNELS = ["granulation", "slough", "eschar", "epithelial"] as const;
