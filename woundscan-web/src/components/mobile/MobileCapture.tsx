"use client";

import { useEffect, useRef, useState } from "react";

type Phase =
  | "checking"
  | "expired"
  | "ready-file" // fallback to native file picker
  | "ready-cam"  // getUserMedia path
  | "captured"
  | "uploading"
  | "uploaded"
  | "error";

const MAX_DIM = 1600;

export function MobileCapture({ sessionId }: { sessionId: string }) {
  const [phase, setPhase] = useState<Phase>("checking");
  const [error, setError] = useState<string | null>(null);
  const [patientLabel, setPatientLabel] = useState<string>("");
  const [imageDataUrl, setImageDataUrl] = useState<string | null>(null);
  const [notes, setNotes] = useState("");
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Confirm session is valid + decide whether camera API is available.
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await fetch(`/api/capture/sessions/${sessionId}`, { cache: "no-store" });
        if (!res.ok) throw new Error("Session not found.");
        const s = await res.json();
        if (!mounted) return;
        if (s.status === "expired") {
          setPhase("expired");
          return;
        }
        if (s.patientLabel) setPatientLabel(s.patientLabel);
        const hasCam =
          typeof navigator !== "undefined" &&
          !!navigator.mediaDevices &&
          typeof navigator.mediaDevices.getUserMedia === "function";
        setPhase(hasCam ? "ready-cam" : "ready-file");
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        setPhase("error");
      }
    })();
    return () => {
      mounted = false;
      stopStream();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  function stopStream() {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }

  async function startCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 1920 } },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
    } catch {
      setPhase("ready-file");
    }
  }

  useEffect(() => {
    if (phase === "ready-cam") startCamera();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  function captureFromVideo() {
    const v = videoRef.current;
    if (!v) return;
    const w = v.videoWidth;
    const h = v.videoHeight;
    if (!w || !h) return;
    const data = downscaleToDataUrl(v, w, h);
    setImageDataUrl(data);
    stopStream();
    setPhase("captured");
  }

  async function handleFile(file: File) {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result ?? "");
      // Re-encode through canvas to apply downscaling/JPEG.
      const img = new Image();
      img.onload = () => {
        const data = downscaleToDataUrl(img, img.naturalWidth, img.naturalHeight);
        setImageDataUrl(data);
        setPhase("captured");
      };
      img.onerror = () => {
        setImageDataUrl(result);
        setPhase("captured");
      };
      img.src = result;
    };
    reader.readAsDataURL(file);
  }

  async function upload() {
    if (!imageDataUrl) return;
    setPhase("uploading");
    setError(null);
    try {
      const res = await fetch(`/api/capture/sessions/${sessionId}/upload`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ imageDataUrl, notes }),
      });
      if (!res.ok) throw new Error(await res.text());
      setPhase("uploaded");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setPhase("error");
    }
  }

  return (
    <main className="mx-auto flex min-h-[100svh] max-w-md flex-col px-4 py-5 text-sm">
      <header className="mb-4">
        <p className="text-[11px] uppercase tracking-[0.18em] text-ink-muted">
          WoundScan capture
        </p>
        <h1 className="mt-1 font-display text-2xl font-bold text-ink">
          Take the photo here
        </h1>
        {patientLabel && (
          <p className="mt-1 text-xs text-ink-muted">For: {patientLabel}</p>
        )}
      </header>

      {phase === "checking" && (
        <Pane>
          <p className="text-ink-soft">Pairing with desktop…</p>
        </Pane>
      )}

      {phase === "expired" && (
        <Pane tone="warn">
          <p className="text-warn">
            This pairing link has expired. Generate a fresh QR on the desktop and try again.
          </p>
        </Pane>
      )}

      {phase === "ready-cam" && (
        <Pane>
          <div className="overflow-hidden rounded-lg border border-hairline bg-black">
            <video
              ref={videoRef}
              playsInline
              muted
              className="aspect-[3/4] w-full object-cover"
            />
          </div>
          <Tips />
          <button className="btn btn-primary mt-4 w-full justify-center" onClick={captureFromVideo}>
            Take photo
          </button>
          <button
            className="btn btn-secondary mt-2 w-full justify-center"
            onClick={() => {
              stopStream();
              setPhase("ready-file");
            }}
          >
            Use camera roll instead
          </button>
        </Pane>
      )}

      {phase === "ready-file" && (
        <Pane>
          <Tips />
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleFile(f);
            }}
          />
          <button
            className="btn btn-primary mt-4 w-full justify-center"
            onClick={() => fileInputRef.current?.click()}
          >
            Open camera
          </button>
        </Pane>
      )}

      {phase === "captured" && imageDataUrl && (
        <Pane>
          <div className="overflow-hidden rounded-lg border border-hairline">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={imageDataUrl} alt="Captured wound" className="w-full" />
          </div>
          <label className="mt-3 block">
            <span className="label">Notes (optional)</span>
            <textarea
              className="input min-h-[72px]"
              placeholder="e.g. fiducial sticker visible bottom-left, drainage scant"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </label>
          <button className="btn btn-primary mt-3 w-full justify-center" onClick={upload}>
            Send to desktop
          </button>
          <button
            className="btn btn-secondary mt-2 w-full justify-center"
            onClick={() => {
              setImageDataUrl(null);
              setPhase("ready-cam");
            }}
          >
            Retake
          </button>
        </Pane>
      )}

      {phase === "uploading" && (
        <Pane>
          <p className="text-ink-soft">Uploading…</p>
        </Pane>
      )}

      {phase === "uploaded" && (
        <Pane tone="success">
          <p className="text-success">Sent! You can close this tab.</p>
          <p className="mt-1 text-xs text-ink-muted">
            The desktop is rendering the capture now.
          </p>
        </Pane>
      )}

      {phase === "error" && (
        <Pane tone="danger">
          <p className="text-danger">{error ?? "Something went wrong."}</p>
          <button
            className="btn btn-secondary mt-3 w-full justify-center"
            onClick={() => setPhase("ready-cam")}
          >
            Try again
          </button>
        </Pane>
      )}

      <footer className="mt-auto pt-6 text-center text-[10px] text-ink-muted">
        Clinical decision support · not for diagnostic use
      </footer>
    </main>
  );
}

function Pane({ children, tone }: { children: React.ReactNode; tone?: "warn" | "success" | "danger" }) {
  const ring = tone === "warn"    ? "border-warn/40 bg-warn/5"
            : tone === "success"  ? "border-success/40 bg-success/5"
            : tone === "danger"   ? "border-danger/40 bg-danger/5"
            : "border-hairline bg-surface";
  return <section className={`rounded-lg border p-4 ${ring}`}>{children}</section>;
}

function Tips() {
  return (
    <ul className="mt-3 space-y-1 text-xs text-ink-soft">
      <li>• Hold the phone roughly <b>30 cm</b> above the wound.</li>
      <li>• Place the <b>fiducial sticker</b> at the wound edge for scale.</li>
      <li>• Avoid harsh shadows or glare — natural light works best.</li>
    </ul>
  );
}

function downscaleToDataUrl(
  source: HTMLVideoElement | HTMLImageElement,
  width: number,
  height: number,
): string {
  const ratio = Math.min(1, MAX_DIM / Math.max(width, height));
  const w = Math.round(width * ratio);
  const h = Math.round(height * ratio);
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  if (!ctx) return "";
  ctx.drawImage(source as CanvasImageSource, 0, 0, w, h);
  return canvas.toDataURL("image/jpeg", 0.85);
}
