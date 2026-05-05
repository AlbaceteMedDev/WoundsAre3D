"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { QRCodeSVG } from "qrcode.react";

type Status = "idle" | "creating" | "waiting" | "received" | "error";

type Session = {
  id: string;
  status: "pending" | "uploaded" | "expired";
  patientLabel?: string;
  uploadedAt?: number;
};

export function CaptureHandoff() {
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [patientLabel, setPatientLabel] = useState("");
  const [imageDataUrl, setImageDataUrl] = useState<string | null>(null);
  const [notes, setNotes] = useState("");
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const mobileUrl = useMemo(() => {
    if (!session) return "";
    if (typeof window === "undefined") return "";
    return `${window.location.origin}/m/${session.id}`;
  }, [session]);

  async function startSession() {
    setStatus("creating");
    setError(null);
    setImageDataUrl(null);
    setNotes("");
    try {
      const res = await fetch("/api/capture/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ patientLabel: patientLabel || undefined }),
      });
      if (!res.ok) throw new Error(await res.text());
      const s: Session = await res.json();
      setSession(s);
      setStatus("waiting");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setStatus("error");
    }
  }

  function stop() {
    if (pollTimer.current) {
      clearInterval(pollTimer.current);
      pollTimer.current = null;
    }
  }

  // Poll once we have a session.
  useEffect(() => {
    if (!session || status !== "waiting") return;
    pollTimer.current = setInterval(async () => {
      try {
        const res = await fetch(`/api/capture/sessions/${session.id}`, { cache: "no-store" });
        if (!res.ok) return;
        const fresh = await res.json();
        if (fresh.status === "uploaded") {
          stop();
          const img = await fetch(`/api/capture/sessions/${session.id}/image`, { cache: "no-store" });
          if (img.ok) {
            const data = await img.json();
            setImageDataUrl(data.imageDataUrl);
            setNotes(data.notes ?? "");
            setStatus("received");
          }
        } else if (fresh.status === "expired") {
          stop();
          setError("Session expired before the phone uploaded.");
          setStatus("error");
        }
      } catch {
        /* swallow transient errors */
      }
    }, 2000);
    return stop;
  }, [session, status]);

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[420px_1fr]">
      {/* LEFT: QR + status */}
      <section className="card p-5">
        <span className="eyebrow">Step 1 · Pair the phone</span>
        <h2 className="mt-1 font-display text-lg font-semibold text-ink">
          Scan with your phone camera
        </h2>

        <div className="mt-4 space-y-3">
          <label className="block text-sm">
            <span className="label">Patient label (optional)</span>
            <input
              className="input"
              placeholder="e.g. P. Johnson · DFU R plantar"
              value={patientLabel}
              onChange={(e) => setPatientLabel(e.target.value)}
              disabled={status === "waiting" || status === "received"}
            />
          </label>

          {status === "idle" || status === "error" ? (
            <button className="btn btn-primary w-full justify-center" onClick={startSession}>
              {status === "error" ? "Try again" : "Generate QR"}
            </button>
          ) : (
            <button
              className="btn btn-secondary w-full justify-center"
              onClick={() => {
                stop();
                setSession(null);
                setStatus("idle");
                setImageDataUrl(null);
              }}
            >
              Cancel session
            </button>
          )}
        </div>

        {session && (
          <div className="mt-5 flex flex-col items-center gap-3 rounded-md border border-hairline bg-surface-2 p-4">
            <div className="rounded bg-white p-3">
              <QRCodeSVG value={mobileUrl} size={208} level="M" includeMargin={false} />
            </div>
            <div className="w-full break-all rounded bg-surface px-2 py-1.5 text-center font-mono text-[11px] text-ink-muted">
              {mobileUrl}
            </div>
            <StatusPill status={status} />
            <p className="text-center text-xs text-ink-muted">
              Or open the link directly on your phone if scanning isn&apos;t handy.
            </p>
          </div>
        )}

        {error && <p className="mt-3 text-sm text-danger">{error}</p>}
      </section>

      {/* RIGHT: result */}
      <section className="card p-5">
        <span className="eyebrow">Step 2 · Analyse on this computer</span>
        <h2 className="mt-1 font-display text-lg font-semibold text-ink">
          {status === "received" ? "Capture received" : "Waiting for capture…"}
        </h2>

        {status !== "received" && !imageDataUrl && (
          <div className="mt-4 grid h-[420px] place-items-center rounded-md border border-dashed border-hairline bg-surface-2 text-sm text-ink-muted">
            <div className="text-center">
              <p>The photo your phone captures will land here.</p>
              <p className="mt-1 text-xs">2D measurement only — for full 3-D mesh, use the iOS app.</p>
            </div>
          </div>
        )}

        {imageDataUrl && (
          <>
            <div className="mt-4 overflow-hidden rounded-md border border-hairline">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={imageDataUrl} alt="Captured wound" className="w-full" />
            </div>

            <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
              <Metric label="Detected area" value="—" sub="2D, needs scale fiducial" />
              <Metric label="Perimeter" value="—" sub="2D" />
              <Metric label="Tissue mix" value="auto-est" sub="vision model" />
              <Metric label="Quality" value="B" sub="from focus + glare" />
            </div>

            {notes && (
              <div className="mt-4 rounded-md border border-hairline bg-surface-2 p-3 text-sm text-ink-soft">
                <p className="text-[11px] uppercase tracking-[0.14em] text-ink-muted">Phone notes</p>
                <p className="mt-1 whitespace-pre-wrap">{notes}</p>
              </div>
            )}

            <div className="mt-4 flex gap-2">
              <button className="btn btn-primary">Attach to wound case</button>
              <button
                className="btn btn-secondary"
                onClick={() => {
                  setImageDataUrl(null);
                  setSession(null);
                  setStatus("idle");
                }}
              >
                Start a new capture
              </button>
            </div>

            <p className="mt-4 text-[11px] text-ink-muted">
              For depth + 3-D reconstruction, capture again from the iOS app — it uses LiDAR
              and ARKit pose data the phone browser can&apos;t access.
            </p>
          </>
        )}
      </section>
    </div>
  );
}

function StatusPill({ status }: { status: Status }) {
  const map: Record<Status, { label: string; cls: string }> = {
    idle: { label: "Idle", cls: "pill pill-neutral" },
    creating: { label: "Creating session…", cls: "pill pill-accent" },
    waiting: { label: "Waiting for phone upload", cls: "pill pill-accent" },
    received: { label: "Received", cls: "pill pill-success" },
    error: { label: "Error", cls: "pill pill-danger" },
  };
  const s = map[status];
  return <span className={s.cls}>{s.label}</span>;
}

function Metric({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded border border-hairline bg-surface-2 p-2">
      <div className="text-[10px] uppercase tracking-[0.14em] text-ink-muted">{label}</div>
      <div className="mt-0.5 font-display text-base font-semibold text-ink">{value}</div>
      {sub && <div className="text-[10px] text-ink-muted">{sub}</div>}
    </div>
  );
}
