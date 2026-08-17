"use client";

import { useState } from "react";
import { Reveal } from "./Reveal";

type Metric = {
  key: string;
  label: string;
  value: string;
  unit: string;
  note: string;
};

const METRICS: Metric[] = [
  { key: "length", label: "Length", value: "42.0", unit: "mm", note: "major axis, point-cloud geometry" },
  { key: "width", label: "Width", value: "38.0", unit: "mm", note: "minor axis, point-cloud geometry" },
  { key: "depth", label: "Max depth", value: "11.8", unit: "mm", note: "fitted reference plane → wound floor" },
  { key: "bed", label: "Wound bed area", value: "11.2", unit: "cm²", note: "actual boundary, not a bounding box" },
  { key: "peri", label: "Peri-wound area", value: "18.4", unit: "cm²", note: "surrounding zone for sizing + billing" },
];

type Tab = "top" | "section" | "summary";

export function ReportSection() {
  const [tab, setTab] = useState<Tab>("top");
  const [hovered, setHovered] = useState<string | null>(null);

  return (
    <section id="report" className="relative scroll-mt-20 py-20 md:py-28">
      <div className="mk-section">
        <Reveal>
          <span className="eyebrow">The deliverable</span>
          <h2 className="mk-h2 mt-3">
            One scan. <span className="text-gradient">Five measurements.</span> A report that
            stands up.
          </h2>
          <p className="mk-lead">
            Every measurement report pairs structured numbers with visual diagrams and a
            plain-language narrative scoped strictly to objective data — the methodology is
            disclosed on every page.
          </p>
        </Reveal>

        <div className="mt-12 grid items-start gap-8 lg:grid-cols-[1fr_400px]">
          {/* Report card */}
          <Reveal>
            <div className="mk-card overflow-hidden !p-0">
              {/* Chrome bar */}
              <div className="flex items-center justify-between border-b border-hairline bg-surface-2/60 px-4 py-2.5">
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-danger/50" />
                  <span className="h-2.5 w-2.5 rounded-full bg-warn/50" />
                  <span className="h-2.5 w-2.5 rounded-full bg-success/50" />
                </div>
                <p className="font-mono text-[11px] text-ink-muted">
                  measurement_report · MSR-2031 · v1.0
                </p>
                <span className="pill pill-success">Quality A</span>
              </div>

              {/* Tabs */}
              <div className="flex gap-1 border-b border-hairline px-3 pt-2" role="tablist">
                <ReportTab active={tab === "top"} onClick={() => setTab("top")}>
                  Top-view diagram
                </ReportTab>
                <ReportTab active={tab === "section"} onClick={() => setTab("section")}>
                  Cross-section
                </ReportTab>
                <ReportTab active={tab === "summary"} onClick={() => setTab("summary")}>
                  Plain-language summary
                </ReportTab>
              </div>

              <div className="min-h-[380px] p-5 md:p-6">
                {tab === "top" && <TopView hovered={hovered} />}
                {tab === "section" && <CrossSection />}
                {tab === "summary" && <Summary />}
              </div>
            </div>
          </Reveal>

          {/* Metric tiles */}
          <div className="space-y-2.5">
            {METRICS.map((m, i) => (
              <Reveal key={m.key} delay={i * 80}>
                <button
                  type="button"
                  onMouseEnter={() => setHovered(m.key)}
                  onMouseLeave={() => setHovered(null)}
                  onFocus={() => setHovered(m.key)}
                  onBlur={() => setHovered(null)}
                  onClick={() => setTab(m.key === "depth" ? "section" : "top")}
                  className={`w-full rounded-lg border px-4 py-3 text-left transition-all duration-200 ${
                    hovered === m.key
                      ? "border-accent/60 bg-surface shadow-soft"
                      : "border-hairline bg-surface/60"
                  }`}
                >
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="text-sm font-medium text-ink-soft">{m.label}</span>
                    <span className="font-display text-xl font-bold text-ink">
                      {m.value}
                      <span className="ml-1 text-xs font-medium text-ink-muted">{m.unit}</span>
                    </span>
                  </div>
                  <p className="mt-0.5 text-[11px] text-ink-muted">{m.note}</p>
                </button>
              </Reveal>
            ))}
            <Reveal delay={420}>
              <p className="px-1 pt-2 text-[11px] leading-relaxed text-ink-muted">
                Values shown are from the bundled synthetic demonstration mesh (~40 × 40 × 12 mm
                Gaussian wound bed). Hover a metric to highlight it on the diagram.
              </p>
            </Reveal>
          </div>
        </div>
      </div>
    </section>
  );
}

function ReportTab({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={`rounded-t-md px-3 py-2 font-display text-xs font-semibold transition md:text-sm ${
        active
          ? "border-b-2 border-accent text-ink"
          : "border-b-2 border-transparent text-ink-muted hover:text-ink-soft"
      }`}
    >
      {children}
    </button>
  );
}

/** Top-view SVG wound diagram: boundary, peri-wound ring, axes, scale bar. */
function TopView({ hovered }: { hovered: string | null }) {
  const dim = (k: string) => (hovered && hovered !== k ? 0.25 : 1);
  return (
    <figure>
      <svg viewBox="0 0 520 330" className="w-full" role="img" aria-label="Top-view wound diagram with length and width axes, wound bed, and peri-wound ring">
        {/* Peri-wound ring */}
        <g opacity={dim("peri")} style={{ transition: "opacity .2s" }}>
          <path
            d="M110 165 C 105 95, 185 55, 265 62 C 350 70, 420 105, 415 170 C 410 240, 330 285, 250 280 C 165 275, 115 235, 110 165 Z"
            fill="rgb(var(--accent) / 0.06)"
            stroke="rgb(var(--accent) / 0.45)"
            strokeWidth="1.4"
            strokeDasharray="5 5"
          />
          <text x="380" y="70" fontSize="11" fontFamily="var(--font-mono), monospace" fill="rgb(var(--accent))">
            peri-wound 18.4 cm²
          </text>
        </g>

        {/* Wound bed */}
        <g opacity={dim("bed")} style={{ transition: "opacity .2s" }}>
          <path
            className="mk-trace is-on"
            d="M160 165 C 158 118, 210 95, 265 100 C 320 105, 372 128, 368 170 C 364 215, 315 245, 258 240 C 200 235, 162 210, 160 165 Z"
            fill="rgb(var(--danger) / 0.10)"
            stroke="rgb(var(--danger) / 0.8)"
            strokeWidth="2"
          />
          <text x="196" y="222" fontSize="11" fontFamily="var(--font-mono), monospace" fill="rgb(var(--ink-soft))">
            bed 11.2 cm²
          </text>
        </g>

        {/* Length axis */}
        <g opacity={dim("length")} style={{ transition: "opacity .2s" }}>
          <line x1="160" y1="292" x2="368" y2="292" stroke="rgb(var(--accent))" strokeWidth="1.4" />
          <line x1="160" y1="286" x2="160" y2="298" stroke="rgb(var(--accent))" strokeWidth="1.4" />
          <line x1="368" y1="286" x2="368" y2="298" stroke="rgb(var(--accent))" strokeWidth="1.4" />
          <text x="240" y="312" fontSize="11" fontFamily="var(--font-mono), monospace" fill="rgb(var(--accent))">
            L 42.0 mm
          </text>
        </g>

        {/* Width axis */}
        <g opacity={dim("width")} style={{ transition: "opacity .2s" }}>
          <line x1="120" y1="100" x2="120" y2="240" stroke="rgb(var(--accent))" strokeWidth="1.4" />
          <line x1="114" y1="100" x2="126" y2="100" stroke="rgb(var(--accent))" strokeWidth="1.4" />
          <line x1="114" y1="240" x2="126" y2="240" stroke="rgb(var(--accent))" strokeWidth="1.4" />
          <text x="36" y="176" fontSize="11" fontFamily="var(--font-mono), monospace" fill="rgb(var(--accent))">
            W 38.0 mm
          </text>
        </g>

        {/* Depth marker (crosshair at deepest point) */}
        <g opacity={dim("depth")} style={{ transition: "opacity .2s" }}>
          <circle cx="262" cy="168" r="7" fill="none" stroke="rgb(var(--warn))" strokeWidth="1.4" />
          <line x1="262" y1="157" x2="262" y2="179" stroke="rgb(var(--warn))" strokeWidth="1.2" />
          <line x1="251" y1="168" x2="273" y2="168" stroke="rgb(var(--warn))" strokeWidth="1.2" />
          <text x="274" y="156" fontSize="11" fontFamily="var(--font-mono), monospace" fill="rgb(var(--warn))">
            max depth 11.8 mm
          </text>
        </g>

        {/* Scale bar */}
        <g>
          <line x1="424" y1="308" x2="504" y2="308" stroke="rgb(var(--ink-muted))" strokeWidth="1.6" />
          <line x1="424" y1="303" x2="424" y2="313" stroke="rgb(var(--ink-muted))" strokeWidth="1.4" />
          <line x1="504" y1="303" x2="504" y2="313" stroke="rgb(var(--ink-muted))" strokeWidth="1.4" />
          <text x="446" y="300" fontSize="10" fontFamily="var(--font-mono), monospace" fill="rgb(var(--ink-muted))">
            10 mm
          </text>
        </g>
      </svg>
      <figcaption className="mt-2 text-[11px] text-ink-muted">
        Top-view SVG diagram — wound outline, peri-wound ring, length/width axes, scale bar. Exactly
        as rendered in the clinical report.
      </figcaption>
    </figure>
  );
}

/** Cross-section depth profile relative to the fitted skin plane. */
function CrossSection() {
  return (
    <figure>
      <svg viewBox="0 0 520 330" className="w-full" role="img" aria-label="Cross-section wound depth profile relative to the surrounding skin plane">
        {/* Skin plane */}
        <line x1="30" y1="110" x2="490" y2="110" stroke="rgb(var(--ink-muted))" strokeWidth="1.3" strokeDasharray="7 5" />
        <text x="34" y="100" fontSize="11" fontFamily="var(--font-mono), monospace" fill="rgb(var(--ink-muted))">
          fitted reference plane
        </text>

        {/* Tissue fill */}
        <path
          d="M30 110 L 150 110 C 190 112, 205 195, 262 198 C 320 195, 335 112, 372 110 L 490 110 L 490 300 L 30 300 Z"
          fill="rgb(var(--accent) / 0.07)"
        />
        {/* Wound profile */}
        <path
          className="mk-trace is-on"
          d="M150 110 C 190 112, 205 195, 262 198 C 320 195, 335 112, 372 110"
          fill="none"
          stroke="rgb(var(--danger) / 0.85)"
          strokeWidth="2.4"
        />

        {/* Depth arrow */}
        <line x1="262" y1="110" x2="262" y2="198" stroke="rgb(var(--warn))" strokeWidth="1.6" />
        <path d="M258 190 L 262 198 L 266 190" fill="none" stroke="rgb(var(--warn))" strokeWidth="1.6" />
        <text x="272" y="160" fontSize="12" fontFamily="var(--font-mono), monospace" fill="rgb(var(--warn))">
          11.8 mm
        </text>

        {/* Mean depth line */}
        <line x1="150" y1="163" x2="372" y2="163" stroke="rgb(var(--accent))" strokeWidth="1" strokeDasharray="4 4" />
        <text x="378" y="167" fontSize="10" fontFamily="var(--font-mono), monospace" fill="rgb(var(--accent))">
          mean 5.4 mm
        </text>

        {/* Uncertainty band */}
        <path
          d="M150 106 C 190 108, 205 191, 262 194 C 320 191, 335 108, 372 106 L 372 114 C 335 116, 320 199, 262 202 C 205 199, 190 116, 150 114 Z"
          fill="rgb(var(--warn) / 0.12)"
        />
        <text x="34" y="290" fontSize="10" fontFamily="var(--font-mono), monospace" fill="rgb(var(--ink-muted))">
          shaded band: ±0.3 mm measurement uncertainty (95% CI, Monte Carlo)
        </text>
      </svg>
      <figcaption className="mt-2 text-[11px] text-ink-muted">
        Cross-section depth profile — wound floor relative to the surrounding skin plane, with
        explicit uncertainty bounds. Surface photographs cannot capture this dimension.
      </figcaption>
    </figure>
  );
}

/** Bedrock-style plain-language narration, guardrailed to objective data. */
function Summary() {
  return (
    <div className="mx-auto max-w-xl">
      <div className="rounded-lg border border-hairline bg-surface-2/50 p-5">
        <p className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-widest text-ink-muted">
          <span className="mk-live-dot inline-block h-1.5 w-1.5 rounded-full bg-success" />
          generated summary · objective data only
        </p>
        <div className="prose-sm mt-4 space-y-3 text-sm leading-relaxed text-ink-soft">
          <p>
            This measurement, captured on <strong className="text-ink">March 14, 2026 at 10:42</strong>,
            records a wound on the left lateral ankle measuring{" "}
            <strong className="text-ink">42.0 mm in length</strong> and{" "}
            <strong className="text-ink">38.0 mm in width</strong>, with a wound bed area of{" "}
            <strong className="text-ink">11.2 cm²</strong> computed from the traced boundary.
          </p>
          <p>
            Maximum depth measured <strong className="text-ink">11.8 mm</strong> from the fitted
            skin plane to the wound floor; mean depth was{" "}
            <strong className="text-ink">5.4 mm</strong>. The peri-wound zone measured{" "}
            <strong className="text-ink">18.4 cm²</strong>. Compared with the prior measurement of
            March 7, wound bed area decreased by 9.7%.
          </p>
          <p className="rounded border-l-2 border-accent/50 bg-accent/5 px-3 py-2 text-[13px]">
            This summary describes captured measurement data only. It contains no diagnosis,
            staging, or treatment recommendation — the clinician retains full decision authority.
          </p>
        </div>
      </div>
      <p className="mt-3 text-center text-[11px] text-ink-muted">
        Narration is generated with guardrails that block clinical interpretation, diagnosis, and
        staging language.
      </p>
    </div>
  );
}
