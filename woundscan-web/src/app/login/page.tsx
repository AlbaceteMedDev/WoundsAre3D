"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import Link from "next/link";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, totp_code: totpCode }),
      });
      if (!res.ok) {
        setError("Sign-in failed. Check credentials and TOTP.");
        return;
      }
      router.push("/dashboard");
    } catch {
      setError("Network error. Try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-12">
      <Link href="/" aria-label="WoundScan home" className="mb-8 inline-block">
        <Image
          src="/logo.png"
          width={468}
          height={263}
          alt="WoundScan — powered by Albacete MedDev"
          priority
          className="h-auto w-56 dark:invert"
        />
      </Link>

      <div className="card p-6">
        <span className="eyebrow">Provider portal</span>
        <h1 className="mt-2 font-display text-2xl font-bold text-ink">Sign in</h1>
        <p className="mt-1 text-sm text-ink-muted">Email, password, and your six-digit TOTP code.</p>
        <form onSubmit={submit} className="mt-6 space-y-3">
          <label className="block text-sm">
            <span className="label">Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input"
              autoComplete="email"
              required
            />
          </label>
          <label className="block text-sm">
            <span className="label">Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input"
              autoComplete="current-password"
              required
            />
          </label>
          <label className="block text-sm">
            <span className="label">TOTP code</span>
            <input
              type="text"
              inputMode="numeric"
              pattern="[0-9]{6}"
              placeholder="123456"
              value={totpCode}
              onChange={(e) => setTotpCode(e.target.value)}
              className="input font-mono tracking-[0.4em]"
              autoComplete="one-time-code"
              required
            />
          </label>
          {error && <p className="text-sm text-danger">{error}</p>}
          <button type="submit" disabled={loading} className="btn btn-primary w-full">
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>

      <p className="mt-6 text-xs text-ink-muted">
        Need access? Email <a className="text-accent hover:text-accent-bright" href="mailto:gabe@albacetemeddev.com">gabe@albacetemeddev.com</a>.
      </p>
    </main>
  );
}
