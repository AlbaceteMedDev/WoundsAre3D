import { NextRequest, NextResponse } from "next/server";
import { uploadToSession } from "@/lib/captureStore";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST(req: NextRequest, ctx: { params: { id: string } }) {
  const body = await req.json().catch(() => null);
  if (!body?.imageDataUrl || typeof body.imageDataUrl !== "string") {
    return NextResponse.json({ error: "imageDataUrl required" }, { status: 400 });
  }
  if (!body.imageDataUrl.startsWith("data:image/")) {
    return NextResponse.json({ error: "imageDataUrl must be a data: URL" }, { status: 400 });
  }
  // Cap at ~5MB to keep the in-memory store bounded.
  if (body.imageDataUrl.length > 7_000_000) {
    return NextResponse.json({ error: "image too large (>5MB)" }, { status: 413 });
  }
  const updated = uploadToSession(ctx.params.id, body.imageDataUrl, body.notes);
  if (!updated) return NextResponse.json({ error: "session not found" }, { status: 404 });
  return NextResponse.json({ status: updated.status, uploadedAt: updated.uploadedAt });
}
