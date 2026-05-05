import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";

const API_BASE = process.env.API_URL ?? "http://localhost:8000";

export const dynamic = "force-dynamic";

const PASSTHROUGH_RESPONSE_HEADERS = [
  "content-type",
  "content-length",
  "content-disposition",
  "cache-control",
  "etag",
  "last-modified",
] as const;

async function forward(req: NextRequest, params: { path: string[] }) {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const path = "/" + params.path.join("/");
  const url = `${API_BASE}${path}${req.nextUrl.search}`;

  const headers = new Headers();
  headers.set("Authorization", `Bearer ${session.token}`);
  const incoming = req.headers.get("content-type");
  if (incoming) headers.set("Content-Type", incoming);
  const accept = req.headers.get("accept");
  if (accept) headers.set("Accept", accept);

  const init: RequestInit = {
    method: req.method,
    headers,
    cache: "no-store",
    redirect: "manual",
  };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.arrayBuffer();
  }

  const upstream = await fetch(url, init);

  const out = new Headers();
  for (const name of PASSTHROUGH_RESPONSE_HEADERS) {
    const v = upstream.headers.get(name);
    if (v) out.set(name, v);
  }

  return new NextResponse(upstream.body, { status: upstream.status, headers: out });
}

export async function GET(req: NextRequest, ctx: { params: { path: string[] } }) {
  return forward(req, ctx.params);
}
export async function POST(req: NextRequest, ctx: { params: { path: string[] } }) {
  return forward(req, ctx.params);
}
export async function PUT(req: NextRequest, ctx: { params: { path: string[] } }) {
  return forward(req, ctx.params);
}
export async function PATCH(req: NextRequest, ctx: { params: { path: string[] } }) {
  return forward(req, ctx.params);
}
export async function DELETE(req: NextRequest, ctx: { params: { path: string[] } }) {
  return forward(req, ctx.params);
}
