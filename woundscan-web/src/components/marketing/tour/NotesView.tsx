"use client";

import { useState } from "react";
import { Chip, ViewHeader } from "./shared";

const TEMPLATES = [
  "DFU Follow-Up",
  "Pressure Injury",
  "Venous Leg Ulcer",
  "Surgical Dehiscence",
  "Policy & LCD Alignment",
];

const RECENT = [
  { name: "Note · P. Johnson · v6", at: "today 09:34", state: "draft" },
  { name: "Note · J. Carter · v3", at: "today 08:55", state: "signed" },
  { name: "Note · M. Chen · v9", at: "yesterday", state: "signed" },
  { name: "Note · S. Cole · v4", at: "Apr 28", state: "signed" },
] as const;

/**
 * Audit-safe notes — template chips switch context, measurement fields
 * arrive locked from the engine, and Sign & lock runs the real flow:
 * draft → signed with timestamp + audit-chain entry.
 */
export function NotesView() {
  const [template, setTemplate] = useState(0);
  const [signed, setSigned] = useState(false);

  return (
    <div className="space-y-4">
      <ViewHeader
        title="Audit-Safe Notes"
        sub="Documentation anchored to instrument data — try signing the draft"
      />

      <div className="flex flex-wrap gap-1.5">
        {TEMPLATES.map((t, i) => (
          <Chip key={t} active={template === i} onClick={() => setTemplate(i)}>
            {t}
          </Chip>
        ))}
      </div>

      <div className="grid gap-3 lg:grid-cols-[1fr_240px]">
        <div className="card overflow-hidden !p-0">
          <header className="flex flex-wrap items-center justify-between gap-2 border-b border-hairline p-4">
            <div>
              <span className="eyebrow">Drafting · {TEMPLATES[template]}</span>
              <h4 className="mt-1 font-display text-sm font-semibold text-ink">
                Patricia Johnson · visit 6
              </h4>
              <p className="text-[11px] text-ink-muted">
                Anchored to measurement Apr 29, 2026 · auto-saved 14s ago
              </p>
            </div>
            {signed ? (
              <span className="pill pill-success">signed &amp; locked · Dr. Morgan · 09:41</span>
            ) : (
              <button type="button" onClick={() => setSigned(true)} className="btn btn-primary">
                Sign &amp; lock
              </button>
            )}
          </header>

          <div className={`space-y-4 p-4 text-xs leading-relaxed ${signed ? "opacity-90" : ""}`}>
            <section>
              <p className="mb-1.5 font-semibold uppercase tracking-wider text-ink-muted">
                Measurements (locked from capture)
              </p>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {[
                  ["Bed area", "11.2 cm²"],
                  ["Max depth", "11.8 mm"],
                  ["Peri-wound", "18.4 cm²"],
                  ["Δ vs prior", "−9.7%"],
                ].map(([k, v]) => (
                  <div key={k} className="rounded border border-hairline bg-surface-2 px-2 py-1.5">
                    <div className="text-[10px] uppercase tracking-wider text-ink-muted">{k} 🔒</div>
                    <div className="font-display text-sm font-semibold text-ink">{v}</div>
                  </div>
                ))}
              </div>
            </section>

            <section>
              <p className="mb-1.5 font-semibold uppercase tracking-wider text-ink-muted">
                Tissue composition (locked from measurement)
              </p>
              <div className="flex h-2.5 overflow-hidden rounded-full">
                <span className="bg-warn" style={{ width: "62%" }} title="Granulation 62%" />
                <span className="bg-danger" style={{ width: "28%" }} title="Slough 28%" />
                <span className="bg-ink-muted" style={{ width: "10%" }} title="Eschar 10%" />
              </div>
              <p className="mt-1 text-[11px] text-ink-muted">
                Granulation 62% (+8) · Slough 28% (−6) · Eschar 10% (−2)
              </p>
            </section>

            <section>
              <p className="mb-1.5 font-semibold uppercase tracking-wider text-ink-muted">
                Subjective findings (editable)
              </p>
              <textarea
                readOnly={signed}
                className="input min-h-[64px] text-xs"
                defaultValue="67F with T2DM presents for follow-up of right plantar 1st MTP DFU. Reports improved comfort with offloading boot. Denies new drainage, fever, increased pain. Adherent to plan."
              />
            </section>

            {signed && (
              <p className="rounded border-l-2 border-success/60 bg-success/5 px-3 py-2 font-mono text-[10px] text-ink-soft">
                signature dr.morgan@practice · 2026-05-12T09:41:07Z · entry #4,183 appended to
                tamper-evident audit chain ✓ — note contents are now immutable
              </p>
            )}
          </div>
        </div>

        <aside className="card p-3">
          <span className="eyebrow">Recent documents</span>
          <ul className="mt-2 space-y-1.5">
            {RECENT.map((d, i) => (
              <li
                key={d.name}
                className="flex items-center justify-between gap-2 rounded-md border border-hairline bg-surface px-2.5 py-2 text-[11px]"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium text-ink">{d.name}</p>
                  <p className="text-ink-muted">{d.at}</p>
                </div>
                <span className={`pill ${(i === 0 && !signed) || d.state === "draft" ? (i === 0 && signed ? "pill-success" : "pill-warn") : "pill-success"}`}>
                  {i === 0 ? (signed ? "signed" : "draft") : d.state}
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-[10px] leading-relaxed text-ink-muted">
            Every signature appends to the hash chain — see Admin → Audit log to verify it.
          </p>
        </aside>
      </div>
    </div>
  );
}
