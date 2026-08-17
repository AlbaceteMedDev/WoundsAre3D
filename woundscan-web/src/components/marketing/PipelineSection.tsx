"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Reveal } from "./Reveal";

type Step = {
  key: string;
  num: string;
  title: string;
  tag: string;
  body: string;
  detail: string[];
};

const STEPS: Step[] = [
  {
    key: "capture",
    num: "01",
    title: "Capture",
    tag: "iPhone · ARKit + LiDAR",
    body: "A clinician positions an iPhone over the wound. The app captures a burst of 60 LiDAR depth frames in four seconds, with live motion and fiducial feedback guiding the hold.",
    detail: ["60-frame multi-frame burst", "Live motion + fiducial guidance", "Offline queue with retry"],
  },
  {
    key: "fuse",
    num: "02",
    title: "Reconstruct",
    tag: "Sensor fusion · uncertainty-aware",
    body: "Frames are fused into a single 3D surface using heteroscedastic Gaussian-process fusion with Monte Carlo uncertainty — every point on the mesh knows how confident it is.",
    detail: ["Heteroscedastic GP fusion", "Monte Carlo uncertainty bounds", "Millimeter-scale point cloud"],
  },
  {
    key: "segment",
    num: "03",
    title: "Segment",
    tag: "ML boundary detection",
    body: "A segmentation model proposes the wound boundary from the captured imagery — the outline every measurement derives from — with clinician review and manual refinement always available.",
    detail: ["SAM-based boundary proposal", "Clinician-adjustable outline", "Versioned ML weights"],
  },
  {
    key: "measure",
    num: "04",
    title: "Measure",
    tag: "3D geometry engine",
    body: "From the fused mesh and boundary, the engine computes length, width, true depth from a fitted reference plane, non-rectangular wound bed area, and the peri-wound zone.",
    detail: ["Depth from fitted skin plane", "Actual-boundary bed area", "Peri-wound area for sizing"],
  },
  {
    key: "report",
    num: "05",
    title: "Report",
    tag: "Diagrams + plain language",
    body: "Within minutes: a structured report with top-view and cross-section diagrams and a plain-language summary scoped to objective data — no diagnosis, no staging language, full methodology disclosed.",
    detail: ["Top-view SVG wound diagram", "Cross-section depth profile", "PDF / CSV / FHIR export"],
  },
];

const AUTO_ADVANCE_MS = 5200;

export function PipelineSection() {
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(false);
  const sectionRef = useRef<HTMLElement | null>(null);
  const [inView, setInView] = useState(false);

  // Only auto-advance while the section is on screen and not hovered.
  useEffect(() => {
    const el = sectionRef.current;
    if (!el) return;
    const io = new IntersectionObserver((e) => setInView(e.some((x) => x.isIntersecting)), {
      threshold: 0.25,
    });
    io.observe(el);
    return () => io.disconnect();
  }, []);

  useEffect(() => {
    if (!inView || paused) return;
    const id = setInterval(() => setActive((a) => (a + 1) % STEPS.length), AUTO_ADVANCE_MS);
    return () => clearInterval(id);
  }, [inView, paused]);

  const select = useCallback((i: number) => {
    setActive(i);
    setPaused(true);
  }, []);

  const step = STEPS[active]!;

  return (
    <section
      id="pipeline"
      ref={sectionRef}
      className="relative scroll-mt-20 border-y border-hairline bg-surface/40 py-20 md:py-28"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      <div className="mk-section">
        <Reveal>
          <span className="eyebrow">How it works</span>
          <h2 className="mk-h2 mt-3">Scan to structured report, in five stages.</h2>
          <p className="mk-lead">
            The full pipeline runs end-to-end on AWS — from LiDAR frames on the device to a
            defensible measurement report in the portal, typically inside five minutes.
          </p>
        </Reveal>

        <div className="mt-12 grid gap-8 lg:grid-cols-[380px_1fr]">
          {/* Step list */}
          <Reveal>
            <ol className="space-y-1.5" role="tablist" aria-label="Pipeline stages">
              {STEPS.map((s, i) => (
                <li key={s.key}>
                  <button
                    type="button"
                    role="tab"
                    aria-selected={i === active}
                    onClick={() => select(i)}
                    className={`group relative w-full overflow-hidden rounded-lg border px-4 py-3.5 text-left transition-all duration-300 ${
                      i === active
                        ? "border-accent/50 bg-surface shadow-soft"
                        : "border-transparent hover:border-hairline hover:bg-surface/60"
                    }`}
                  >
                    {/* Auto-advance progress rail */}
                    {i === active && !paused && inView && (
                      <span
                        aria-hidden
                        className="absolute bottom-0 left-0 h-[2px] bg-accent/70"
                        style={{
                          animation: `mk-progress ${AUTO_ADVANCE_MS}ms linear forwards`,
                        }}
                      />
                    )}
                    <span className="flex items-center gap-3">
                      <span
                        className={`font-mono text-xs ${i === active ? "text-accent" : "text-ink-muted"}`}
                      >
                        {s.num}
                      </span>
                      <span
                        className={`font-display text-sm font-semibold ${
                          i === active ? "text-ink" : "text-ink-soft"
                        }`}
                      >
                        {s.title}
                      </span>
                      <span className="ml-auto hidden text-[11px] text-ink-muted sm:inline">
                        {s.tag}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ol>
          </Reveal>

          {/* Active step detail + visual */}
          <Reveal delay={120}>
            <div className="mk-card relative min-h-[340px] overflow-hidden !p-0">
              <div className="grid h-full md:grid-cols-[1fr_240px]">
                <div className="p-6 md:p-8">
                  <p className="font-mono text-[11px] uppercase tracking-widest text-accent">
                    Stage {step.num} — {step.tag}
                  </p>
                  <h3 className="mt-2 font-display text-2xl font-bold text-ink">{step.title}</h3>
                  <p className="mt-3 max-w-lg text-sm leading-relaxed text-ink-soft md:text-base">
                    {step.body}
                  </p>
                  <ul className="mt-5 space-y-2">
                    {step.detail.map((d) => (
                      <li key={d} className="flex items-center gap-2.5 text-sm text-ink-soft">
                        <CheckDot />
                        {d}
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="relative hidden items-center justify-center border-l border-hairline bg-surface-2/50 md:flex">
                  <StepGlyph step={step.key} />
                </div>
              </div>
            </div>
          </Reveal>
        </div>
      </div>

      {/* Local keyframes for the progress rail */}
      <style jsx>{`
        @keyframes mk-progress {
          from {
            width: 0%;
          }
          to {
            width: 100%;
          }
        }
      `}</style>
    </section>
  );
}

function CheckDot() {
  return (
    <span className="grid h-[18px] w-[18px] shrink-0 place-items-center rounded-full bg-accent/10">
      <svg width="9" height="9" viewBox="0 0 10 10" fill="none" aria-hidden>
        <path d="M1.5 5.5l2.3 2.3L8.5 2.5" stroke="rgb(var(--accent))" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </span>
  );
}

/** Minimal animated glyph per stage — SVG, token-colored, no assets. */
function StepGlyph({ step }: { step: string }) {
  const stroke = "rgb(var(--accent))";
  const soft = "rgb(var(--ink-muted))";
  switch (step) {
    case "capture":
      return (
        <svg width="130" height="150" viewBox="0 0 130 150" fill="none" aria-hidden>
          <rect x="35" y="15" width="60" height="120" rx="10" stroke={soft} strokeWidth="2" />
          <circle cx="65" cy="126" r="4" stroke={soft} strokeWidth="1.5" />
          <path className="mk-flow" d="M65 55 L30 95 M65 55 L65 100 M65 55 L100 95" stroke={stroke} strokeWidth="1.5" />
          <circle cx="65" cy="55" r="6" fill={stroke} opacity="0.85" />
        </svg>
      );
    case "fuse":
      return (
        <svg width="140" height="140" viewBox="0 0 140 140" fill="none" aria-hidden>
          {[0, 1, 2, 3].map((i) => (
            <path
              key={i}
              d={`M20 ${45 + i * 16} Q 70 ${20 + i * 16} 120 ${45 + i * 16}`}
              stroke={i === 3 ? stroke : soft}
              strokeWidth={i === 3 ? 2 : 1.2}
              opacity={i === 3 ? 1 : 0.5}
            />
          ))}
          <path className="mk-flow" d="M70 30 V 118" stroke={stroke} strokeWidth="1.4" />
        </svg>
      );
    case "segment":
      return (
        <svg width="140" height="140" viewBox="0 0 140 140" fill="none" aria-hidden>
          <ellipse cx="70" cy="70" rx="44" ry="34" stroke={soft} strokeWidth="1.2" opacity="0.5" />
          <path
            className="mk-flow"
            d="M40 70 C 40 50, 60 42, 74 46 C 96 50, 104 62, 98 78 C 92 94, 66 100, 52 90 C 42 84, 40 78, 40 70 Z"
            stroke={stroke}
            strokeWidth="2"
          />
          <circle cx="40" cy="70" r="3.5" fill={stroke} />
          <circle cx="98" cy="78" r="3.5" fill={stroke} />
        </svg>
      );
    case "measure":
      return (
        <svg width="140" height="140" viewBox="0 0 140 140" fill="none" aria-hidden>
          <path d="M25 55 Q 70 20 115 55" stroke={soft} strokeWidth="1.5" />
          <path d="M25 55 Q 55 95 70 96 Q 85 95 115 55" stroke={stroke} strokeWidth="2" />
          <path className="mk-flow" d="M25 55 H 115" stroke={soft} strokeWidth="1.2" />
          <path className="mk-flow" d="M70 55 V 96" stroke={stroke} strokeWidth="1.4" />
          <text x="76" y="80" fill={stroke} fontSize="10" fontFamily="var(--font-mono), monospace">
            11.8mm
          </text>
        </svg>
      );
    default:
      return (
        <svg width="130" height="150" viewBox="0 0 130 150" fill="none" aria-hidden>
          <rect x="25" y="15" width="80" height="110" rx="6" stroke={soft} strokeWidth="2" />
          <path d="M38 35 H 92 M38 50 H 92 M38 65 H 74" stroke={soft} strokeWidth="1.5" opacity="0.6" />
          <ellipse cx="55" cy="95" rx="16" ry="11" stroke={stroke} strokeWidth="1.5" />
          <path className="mk-flow" d="M25 138 H 105" stroke={stroke} strokeWidth="1.4" />
        </svg>
      );
  }
}
