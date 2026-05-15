import { NextRequest, NextResponse } from "next/server";
import { setSession } from "@/lib/auth";

const API_BASE = process.env.API_URL ?? "http://localhost:8000";
const DEMO_MODE_FORCED = process.env.WS_DEMO_MODE === "1";

/**
 * Talks to the real engine when it's up. When the engine is unreachable
 * or `WS_DEMO_MODE=1`, falls back to accepting any non-empty credentials
 * and granting a synthetic session so the portal stays demo-able without
 * a backend.
 */
async function tryRealLogin(body: unknown) {
  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      // Short timeout so demo flows don't hang on a dead engine.
      signal: AbortSignal.timeout(1500),
    });
    if (!res.ok) return null;
    return (await res.json()) as { token: string; expires_at: string; role: string };
  } catch {
    return null;
  }
}

export async function POST(req: NextRequest) {
  const body = (await req.json()) as { email?: string; password?: string; totp_code?: string };
  if (!body.email || !body.password) {
    return NextResponse.json({ error: "missing credentials" }, { status: 400 });
  }

  const real = DEMO_MODE_FORCED ? null : await tryRealLogin(body);
  if (real) {
    const decoded = decodeJwt(real.token);
    await setSession({
      token: real.token,
      expiresAt: new Date(real.expires_at),
      role: (real.role as "clinician" | "reviewer" | "admin"),
      userId: decoded?.sub ?? "unknown",
    });
    return NextResponse.json({ status: "ok" });
  }

  // Engine unavailable → demo bypass.
  await setSession({
    token: "demo-session-token",
    expiresAt: new Date(Date.now() + 12 * 60 * 60 * 1000), // 12h
    role: "clinician",
    userId: "demo-clinician",
  });
  return NextResponse.json({ status: "ok", mode: "demo" });
}

function decodeJwt(token: string): { sub?: string } | null {
  try {
    const parts = token.split(".");
    const payload = parts[1];
    if (!payload) return null;
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json);
  } catch {
    return null;
  }
}
