"use client";

import Link from "next/link";
import dynamic from "next/dynamic";

const HeroScene = dynamic(() => import("./HeroScene").then((m) => m.HeroScene), {
  ssr: false,
  loading: () => (
    <div
      className="grid h-full w-full place-items-center rounded-2xl"
      style={{ background: "radial-gradient(ellipse at 50% 40%, #0a1428 0%, #03060d 75%)" }}
    >
      <span className="font-mono text-xs text-cyan-200/70">initializing 3D viewport…</span>
    </div>
  ),
});

export function Hero() {
  return (
    <section className="relative overflow-hidden pb-16 pt-28 md:pb-24 md:pt-36">
      {/* Backdrop layers */}
      <div aria-hidden className="mk-grid-bg absolute inset-0" />
      <div
        aria-hidden
        className="absolute -top-40 left-1/2 h-[560px] w-[880px] -translate-x-1/2 rounded-full opacity-40 blur-3xl"
        style={{
          background:
            "radial-gradient(closest-side, rgb(var(--accent) / 0.35), transparent 70%)",
        }}
      />

      <div className="mk-section relative grid items-center gap-12 lg:grid-cols-[1.05fr_1fr]">
        <div>
          <span className="mk-rise mk-chip" style={{ "--rise-delay": "0ms" } as React.CSSProperties}>
            <span className="mk-live-dot inline-block h-1.5 w-1.5 rounded-full bg-success" />
            AWS-validated proof of concept · 510(k)-ready architecture
          </span>

          <h1
            className="mk-rise mt-5 font-display text-4xl font-bold leading-[1.06] tracking-tight text-ink sm:text-5xl xl:text-6xl"
            style={{ "--rise-delay": "80ms" } as React.CSSProperties}
          >
            The wound has depth.
            <br />
            <span className="text-gradient">Now your documentation does too.</span>
          </h1>

          <p
            className="mk-rise mt-6 max-w-xl text-base leading-relaxed text-ink-soft md:text-lg"
            style={{ "--rise-delay": "160ms" } as React.CSSProperties}
          >
            StrataMetric&rsquo;s AI Wound Scan turns a four-second iPhone LiDAR scan into an objective,
            reproducible 3D wound measurement — length, width, <strong className="text-ink">true depth</strong>,
            wound bed and peri-wound area — with audit-defensible documentation generated in minutes,
            at the point of care.
          </p>

          <div
            className="mk-rise mt-8 flex flex-wrap items-center gap-3"
            style={{ "--rise-delay": "240ms" } as React.CSSProperties}
          >
            <a href="#demo" className="btn btn-primary px-5 py-2.5 text-base">
              Explore the live demo
              <span aria-hidden>→</span>
            </a>
            <Link href="/login" className="btn btn-secondary px-5 py-2.5 text-base">
              Portal sign in
            </Link>
          </div>

          <dl
            className="mk-rise mt-10 grid max-w-lg grid-cols-3 gap-6"
            style={{ "--rise-delay": "320ms" } as React.CSSProperties}
          >
            <HeroStat value="4 s" label="LiDAR burst capture" />
            <HeroStat value="±mm" label="instrument precision" />
            <HeroStat value="< 5 min" label="scan to report" />
          </dl>
        </div>

        <div
          className="mk-rise relative aspect-[4/3.4] w-full sm:aspect-[4/3]"
          style={{ "--rise-delay": "200ms" } as React.CSSProperties}
        >
          {/* Orbit ring accent behind the canvas */}
          <div
            aria-hidden
            className="mk-orbit absolute -inset-6 rounded-full opacity-25"
            style={{
              background:
                "conic-gradient(from 0deg, transparent 0deg, rgb(var(--accent) / 0.5) 40deg, transparent 90deg, transparent 200deg, rgb(var(--gold) / 0.4) 250deg, transparent 300deg)",
              maskImage: "radial-gradient(closest-side, transparent 86%, black 88%, black 92%, transparent 94%)",
              WebkitMaskImage:
                "radial-gradient(closest-side, transparent 86%, black 88%, black 92%, transparent 94%)",
            }}
          />
          <div className="absolute inset-0 overflow-hidden rounded-2xl border border-hairline shadow-elevated">
            <HeroScene />
          </div>
        </div>
      </div>
    </section>
  );
}

function HeroStat({ value, label }: { value: string; label: string }) {
  return (
    <div>
      <dt className="sr-only">{label}</dt>
      <dd className="font-display text-2xl font-bold text-ink">{value}</dd>
      <dd className="mt-1 text-xs leading-snug text-ink-muted">{label}</dd>
    </div>
  );
}
