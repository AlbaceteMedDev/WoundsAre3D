/**
 * In-memory capture-session store for desktop ↔ phone handoff.
 *
 * The desktop /capture/handoff page creates a session and shows a QR
 * pointing the phone at /m/[id]. The phone takes a photo, posts it to
 * /api/capture/sessions/[id]/upload. The desktop polls the same id
 * and renders the photo + measurement when it arrives.
 *
 * Development-only — wire to S3 + the engine for production. Sessions
 * expire after 30 minutes.
 */

type Status = "pending" | "uploaded" | "expired";

export type CaptureSession = {
  id: string;
  status: Status;
  createdAt: number;
  patientLabel?: string;
  uploadedAt?: number;
  imageDataUrl?: string;
  notes?: string;
};

const TTL_MS = 30 * 60 * 1000;

declare global {
  // eslint-disable-next-line no-var
  var __captureStore: Map<string, CaptureSession> | undefined;
}

const store: Map<string, CaptureSession> =
  globalThis.__captureStore ?? (globalThis.__captureStore = new Map());

function sweep() {
  const now = Date.now();
  for (const [id, s] of store) {
    if (now - s.createdAt > TTL_MS) {
      s.status = "expired";
      if (now - s.createdAt > TTL_MS * 2) store.delete(id);
    }
  }
}

export function createSession(patientLabel?: string): CaptureSession {
  sweep();
  const id = randomId();
  const session: CaptureSession = {
    id,
    status: "pending",
    createdAt: Date.now(),
    patientLabel,
  };
  store.set(id, session);
  return session;
}

export function getSession(id: string): CaptureSession | null {
  sweep();
  return store.get(id) ?? null;
}

export function uploadToSession(
  id: string,
  imageDataUrl: string,
  notes?: string,
): CaptureSession | null {
  sweep();
  const s = store.get(id);
  if (!s) return null;
  if (s.status === "expired") return s;
  s.status = "uploaded";
  s.uploadedAt = Date.now();
  s.imageDataUrl = imageDataUrl;
  s.notes = notes;
  store.set(id, s);
  return s;
}

function randomId(): string {
  const bytes = new Uint8Array(8);
  crypto.getRandomValues(bytes);
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}
