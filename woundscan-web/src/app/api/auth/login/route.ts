import { NextRequest, NextResponse } from "next/server";
import { setSession } from "@/lib/auth";

const API_BASE = process.env.API_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    return NextResponse.json({ error: "Invalid credentials" }, { status: 401 });
  }
  const json = (await res.json()) as { token: string; expires_at: string; role: string };

  // Decode JWT to extract user id (lightweight; not verifying signature here —
  // the engine API is authoritative on what's valid).
  const decoded = decodeJwt(json.token);
  await setSession({
    token: json.token,
    expiresAt: new Date(json.expires_at),
    role: (json.role as "clinician" | "reviewer" | "admin"),
    userId: decoded?.sub ?? "unknown",
  });
  return NextResponse.json({ status: "ok" });
}

function decodeJwt(token: string): { sub?: string } | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = parts[1];
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json);
  } catch {
    return null;
  }
}
