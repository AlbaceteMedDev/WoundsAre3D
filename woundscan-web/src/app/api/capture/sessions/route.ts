import { NextRequest, NextResponse } from "next/server";
import { createSession } from "@/lib/captureStore";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const session = createSession(body?.patientLabel);
  return NextResponse.json(session);
}
