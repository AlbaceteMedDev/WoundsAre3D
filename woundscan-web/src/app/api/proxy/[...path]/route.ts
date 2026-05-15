import { NextRequest, NextResponse } from "next/server";
import { readFile } from "node:fs/promises";
import path from "node:path";
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

const MESH_PATH_RE = /^measurements\/[^/]+\/mesh$/;

/** Serve the bundled `public/demo-wound.obj` for any mesh request. */
async function serveDemoMesh(): Promise<NextResponse> {
  const filePath = path.join(process.cwd(), "public", "demo-wound.obj");
  const data = await readFile(filePath);
  return new NextResponse(data, {
    status: 200,
    headers: { "content-type": "model/obj", "x-ws-demo": "1" },
  });
}

async function forward(req: NextRequest, params: { path: string[] }) {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const joined = params.path.join("/");
  const apiPath = "/" + joined;
  const url = `${API_BASE}${apiPath}${req.nextUrl.search}`;

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
    // Cap upstream stall so demo flows don't hang on a dead engine.
    signal: AbortSignal.timeout(3000),
  };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.arrayBuffer();
  }

  let upstream: Response;
  try {
    upstream = await fetch(url, init);
  } catch {
    // Engine unreachable. For mesh GETs we have a built-in fallback so
    // the 3D viewer still has something to render in demo mode.
    if (req.method === "GET" && MESH_PATH_RE.test(joined)) {
      return serveDemoMesh();
    }
    // Everything else: empty JSON envelope so the caller's defensive
    // fallback path activates instead of surfacing a network error.
    return NextResponse.json({ error: "engine unavailable", demo: true }, { status: 503 });
  }

  // Real engine answered but with an error AND this is a mesh request —
  // fall back to the demo OBJ rather than break the viewer.
  if (!upstream.ok && req.method === "GET" && MESH_PATH_RE.test(joined)) {
    return serveDemoMesh();
  }

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
