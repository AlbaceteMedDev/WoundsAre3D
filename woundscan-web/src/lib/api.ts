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
