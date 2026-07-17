"use client";

import { useState } from "react";
import { Reveal } from "./Reveal";

type Tech = {
  key: string;
  title: string;
  short: string;
  deep: string;
  mono: string;
};

const TECH: Tech[] = [
  {
    key: "lidar",
    title: "LiDAR burst capture",
    short: "60 depth frames in four seconds, guided in real time.",
    deep: "The capture app drives ARKit + LiDAR + AVFoundation together: a multi-frame burst with live motion and fiducial feedback, probe-entry auto-detection with manual fallback, and an offline queue with retry so a dropped connection never loses a scan. Requires only an iPhone 12 Pro or later — hardware clinics already carry.",
    mono: "ARKit · LiDAR · 60f/4s",
  },
  {
    key: "fusion",
    title: "Uncertainty-aware sensor fusion",
    short: "Heteroscedastic Gaussian-process fusion with Monte Carlo bounds.",
    deep: "Instead of naively averaging depth frames, the engine fuses them with a heteroscedastic Gaussian process — noise is modeled per-region, not globally — and propagates uncertainty through every derived measurement via Monte Carlo sampling. Each reported number carries its own confidence interval, and low-confidence captures are flagged for re-scan before they ever reach a report.",
    mono: "GP fusion · MC uncertainty",
  },
  {
    key: "ml",
    title: "ML boundary detection",
    short: "Segmentation-model boundary proposals, clinician-confirmed.",
    deep: "A segmentation model (SAM) proposes the wound outline from captured imagery; the clinician reviews and can refine it before measurements are computed. Model weights are versioned like every other algorithm in the platform, so any historical measurement can be reproduced exactly with the weights that generated it.",
    mono: "SAM · versioned weights",
  },
  {
    key: "geometry",
    title: "True 3D geometry",
    short: "Depth from a fitted plane. Area from the actual boundary.",
    deep: "Length and width come from point-cloud geometry; depth is measured from a least-squares-fitted reference plane of surrounding healthy skin down to the wound floor; wound bed area integrates over the actual traced boundary rather than a bounding rectangle; and the peri-wound zone relevant to product sizing is computed as a first-class output.",
    mono: "plane fit · boundary integral",
  },
  {
    key: "provenance",
    title: "Tamper-evident provenance",
    short: "Every measurement traceable to content-hashed inputs.",
    deep: "Each measurement stores content-hashed inputs, algorithm versions (confidence weights, force-correction tables, ML weights), and a tamper-evident audit hash chain. Combined with the bidirectional regulatory traceability matrix, any number in any report can be traced back to exactly the bytes and code that produced it.",
    mono: "hash chain · full audit",
  },
  {
    key: "validation",
    title: "Six layers of validation",
    short: "Synthetic, property, benchmark, phantom, clinical, regulatory.",
    deep: "The measurement engine ships with 176+ automated tests spanning six validation layers — synthetic meshes with known ground truth, property-based invariants, performance benchmarks, physical phantom calibration, clinical comparison harnesses, and regulatory conformance checks — run in CI on every change.",
    mono: "176+ tests · 6 layers",
  },
];

export function TechnologySection() {
  const [openKey, setOpenKey] = useState<string | null>("fusion");

  return (
    <section id="technology" className="relative scroll-mt-20 py-20 md:py-28">
      <div aria-hidden className="mk-grid-bg absolute inset-0 opacity-60" />
      <div className="mk-section relative">
        <Reveal>
          <span className="eyebrow">Under the hood</span>
          <h2 className="mk-h2 mt-3">
            Built like an instrument,
            <br className="hidden md:block" /> not a camera app.
          </h2>
          <p className="mk-lead">
            Every layer — capture, fusion, segmentation, geometry, provenance — is engineered for
            reproducibility first, because reproducibility is what auditors, partners, and
            regulators actually test.
          </p>
        </Reveal>

        <div className="mt-12 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {TECH.map((t, i) => {
            const open = openKey === t.key;
            return (
              <Reveal key={t.key} delay={(i % 3) * 100}>
                <button
                  type="button"
                  aria-expanded={open}
                  onClick={() => setOpenKey(open ? null : t.key)}
                  className={`mk-card flex h-full w-full flex-col items-stretch justify-start text-left transition-all duration-300 ${
                    open ? "!border-accent/50 shadow-elevated" : ""
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="font-display text-base font-semibold text-ink">{t.title}</h3>
                    <span
                      className={`mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full border border-hairline text-ink-muted transition-transform duration-300 ${
                        open ? "rotate-45 border-accent/50 text-accent" : ""
                      }`}
                      aria-hidden
                    >
                      <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                        <path d="M5 1v8M1 5h8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                      </svg>
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-ink-soft">{t.short}</p>
                  <div
                    className="grid transition-[grid-template-rows] duration-300 ease-out"
                    style={{ gridTemplateRows: open ? "1fr" : "0fr" }}
                  >
                    <div className="overflow-hidden">
                      <p className="mt-3 border-t border-hairline pt-3 text-[13px] leading-relaxed text-ink-soft">
                        {t.deep}
                      </p>
                    </div>
                  </div>
                  <p className="mt-3 font-mono text-[10px] uppercase tracking-wider text-accent">
                    {t.mono}
                  </p>
                </button>
              </Reveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}
