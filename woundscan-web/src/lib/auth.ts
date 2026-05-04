/**
 * Auth helpers: token cookie management for the Next.js app.
 *
 * The JWT is stored in an HTTP-only cookie set by /api/auth/login. Pages
 * verify it server-side via getSession() before rendering.
 */
import { cookies } from "next/headers";

export type Session = {
  token: string;
  expiresAt: Date;
  role: "clinician" | "reviewer" | "admin";
  userId: string;
};

const COOKIE_NAME = "ws_session";

export async function getSession(): Promise<Session | null> {
  const c = cookies().get(COOKIE_NAME);
  if (!c) return null;
  try {
    const parsed = JSON.parse(decodeURIComponent(c.value)) as Session;
    if (new Date(parsed.expiresAt) < new Date()) return null;
    return { ...parsed, expiresAt: new Date(parsed.expiresAt) };
  } catch {
    return null;
  }
}

export async function setSession(session: Session): Promise<void> {
  cookies().set(COOKIE_NAME, encodeURIComponent(JSON.stringify(session)), {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict",
    expires: session.expiresAt,
    path: "/",
  });
}

export async function clearSession(): Promise<void> {
  cookies().delete(COOKIE_NAME);
}
