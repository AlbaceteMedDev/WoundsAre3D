import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";

const API_BASE = process.env.API_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.redirect(new URL("/login", req.url));

  const form = await req.formData();
  const payload = {
    phantom_catalog_id: form.get("phantom_catalog_id"),
    measured_volume_cm3: Number(form.get("measured_volume_cm3")),
    measured_surface_area_cm2: Number(form.get("measured_surface_area_cm2")),
    true_volume_cm3: Number(form.get("true_volume_cm3")),
    true_surface_area_cm2: Number(form.get("true_surface_area_cm2")),
  };

  const res = await fetch(`${API_BASE}/phantom`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.token}`,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    return NextResponse.json({ error: "submission failed" }, { status: 500 });
  }
  return NextResponse.redirect(new URL("/phantom?submitted=1", req.url));
}
