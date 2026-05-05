import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/captureStore";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(_req: NextRequest, ctx: { params: { id: string } }) {
  const s = getSession(ctx.params.id);
  if (!s || !s.imageDataUrl) {
    return NextResponse.json({ error: "no image" }, { status: 404 });
  }
  return NextResponse.json({ imageDataUrl: s.imageDataUrl, notes: s.notes ?? "" });
}
