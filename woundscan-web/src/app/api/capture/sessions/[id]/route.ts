import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/captureStore";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(_req: NextRequest, ctx: { params: { id: string } }) {
  const s = getSession(ctx.params.id);
  if (!s) return NextResponse.json({ error: "not found" }, { status: 404 });
  // Don't ship the data URL on the poll path — desktop fetches the
  // image separately once status flips to "uploaded".
  const { imageDataUrl, ...meta } = s;
  return NextResponse.json({ ...meta, hasImage: Boolean(imageDataUrl) });
}
