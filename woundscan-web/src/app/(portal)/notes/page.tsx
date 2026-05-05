import { AppShell } from "@/components/portal/AppShell";
import { getSession } from "@/lib/auth";

const SMART_TEMPLATES = [
  { name: "HPI Capture", code: "HPI-01", desc: "Subjective complaint, onset, alleviating/exacerbating, prior tx", risk: "low" },
  { name: "Tissue Composition", code: "TIS-04", desc: "Granulation, slough, eschar, epithelial — locked to objective measurement", risk: "low" },
  { name: "Reimbursement Justification", code: "RBJ-08", desc: "Medical necessity, prior care, payer LCD/NCD alignment", risk: "med" },
  { name: "Procedure Note: Graft Application", code: "PROC-03", desc: "UDI, lot, serial, applied area, waste justification", risk: "low" },
  { name: "Rapid Compliance Check", code: "AUDIT-02", desc: "Pre-submission audit pass against current LCDs", risk: "low" },
  { name: "Adverse Event Report", code: "AE-01", desc: "Patient-safety event template with mandatory follow-up", risk: "high" },
];

const ACTION_ITEMS = [
  { item: "Sign 3 drafts from yesterday", who: "Dr. Morgan", due: "today" },
  { item: "Re-attest 2 notes after Q-code update", who: "Dr. Romero", due: "by Fri" },
  { item: "Add MN narrative to CLM-2026-00513", who: "Billing", due: "now" },
];

export default async function NotesPage() {
  const session = await getSession();
  return (
    <AppShell
      title="Audit-Safe Notes"
      subtitle="Code, sign, lock — every progression note hashed and version-pinned"
      user={{ name: "Dr. Rachel Morgan", role: session?.role ?? "clinician" }}
    >
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[260px_1fr_300px]">
        {/* Left: smart templates */}
        <aside className="card flex flex-col gap-3 p-4">
          <header>
            <span className="eyebrow">Smart templates</span>
            <h2 className="mt-1 font-display text-base font-semibold text-ink">
              Pinned to objective data
            </h2>
          </header>
          <ul className="space-y-1.5 text-sm">
            {SMART_TEMPLATES.map((t) => (
              <li
                key={t.code}
                className="cursor-pointer rounded-md border border-hairline bg-surface p-3 transition hover:border-accent/50 hover:bg-surface-2"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-ink">{t.name}</span>
                  <span
                    className={`pill ${
                      t.risk === "high" ? "pill-danger" : t.risk === "med" ? "pill-warn" : "pill-neutral"
                    }`}
                  >
                    {t.code}
                  </span>
                </div>
                <p className="mt-1 text-[11px] leading-relaxed text-ink-muted">{t.desc}</p>
              </li>
            ))}
          </ul>
        </aside>

        {/* Center: editor placeholder */}
        <section className="card flex min-h-[640px] flex-col p-0">
          <header className="flex items-center justify-between border-b border-hairline p-4">
            <div>
              <span className="eyebrow">Drafting</span>
              <h2 className="mt-1 font-display text-base font-semibold text-ink">
                Patricia Johnson · DFU R plantar 1st MTP · visit 6
              </h2>
              <p className="text-xs text-ink-muted">Anchored to measurement Apr 29, 2026 · grade B</p>
            </div>
            <div className="flex gap-2">
              <button className="btn btn-secondary">Save draft</button>
              <button className="btn btn-primary">Sign &amp; lock</button>
            </div>
          </header>

          <div className="flex-1 space-y-4 p-5 text-sm leading-relaxed text-ink-soft">
            <Section title="Subjective">
              <p>67F with T2DM presents for follow-up of right plantar 1st MTP DFU. Reports
              improved comfort with offloading boot. Denies new drainage, fever, increased pain.
              Adherent to plan.</p>
            </Section>
            <Section title="Objective (locked from measurement)">
              <ul className="grid grid-cols-2 gap-x-6 gap-y-1 font-mono text-xs">
                <li>Length 6.72 cm</li>
                <li>Width 4.31 cm</li>
                <li>Depth 1.84 cm</li>
                <li>Surface area 18.72 cm²</li>
                <li>Volume 37.11 cm³</li>
                <li>Quality grade B (overall 0.81)</li>
              </ul>
              <p className="mt-2">Tissue: 62% granulation, 28% slough, 10% eschar. No fluctuance,
              no probe-to-bone. Periwound intact, mild callus 1st MTP.</p>
            </Section>
            <Section title="Assessment">
              <p>Healing trajectory positive: 38% area reduction since intake, on-track per
              30-day Wagner-2 expectation. No clinical signs of infection.</p>
            </Section>
            <Section title="Plan">
              <p>Continue ActiGraft+ q14d, total contact cast change weekly, vascular
              reassessment in 30 days. PCP coordination for A1c. RTC 7 days.</p>
            </Section>
            <Section title="Coding (proposed)">
              <ul className="font-mono text-xs">
                <li>15271 · primary application up to 100cm²</li>
                <li>A2005 · ActiGraft+ ASP per cm²</li>
                <li>97597 · debridement add-on (if performed)</li>
              </ul>
            </Section>
          </div>
        </section>

        {/* Right: patient + risk + compliance */}
        <aside className="space-y-4">
          <div className="card p-4">
            <span className="eyebrow">Patient summary</span>
            <h3 className="mt-1 font-display text-base font-semibold text-ink">Patricia Johnson</h3>
            <p className="text-xs text-ink-muted">67F · MRN-002847 · Medicare A/B</p>
            <ul className="mt-2 space-y-1 text-xs text-ink-soft">
              <li>· DFU R plantar 1st MTP</li>
              <li>· Wagner grade 2</li>
              <li>· A1c 7.8 (Mar 2026)</li>
              <li>· ABI 0.91 R / 0.94 L</li>
            </ul>
          </div>

          <div className="card p-4">
            <span className="eyebrow">Risk &amp; compliance score</span>
            <h3 className="mt-1 font-display text-base font-semibold text-ink">87 / 100</h3>
            <ul className="mt-2 space-y-1.5 text-xs">
              <ScoreRow label="Documentation" pct={92} />
              <ScoreRow label="Coding alignment" pct={88} />
              <ScoreRow label="Photo evidence" pct={95} />
              <ScoreRow label="Signature timeliness" pct={75} />
              <ScoreRow label="LCD/NCD adherence" pct={86} />
            </ul>
          </div>

          <div className="card p-4">
            <span className="eyebrow">Action items</span>
            <ul className="mt-2 space-y-1.5 text-xs">
              {ACTION_ITEMS.map((a, i) => (
                <li key={i} className="flex items-start gap-2 text-ink-soft">
                  <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                  <div>
                    <div>{a.item}</div>
                    <div className="text-ink-muted">
                      {a.who} · {a.due}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </aside>
      </div>
    </AppShell>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h4 className="mb-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-accent">{title}</h4>
      <div className="text-ink-soft">{children}</div>
    </div>
  );
}

function ScoreRow({ label, pct }: { label: string; pct: number }) {
  const tone = pct >= 90 ? "success" : pct >= 80 ? "accent" : "warn";
  return (
    <li>
      <div className="flex justify-between">
        <span className="text-ink-soft">{label}</span>
        <span className="tabular-nums text-ink">{pct}%</span>
      </div>
      <div className="mt-1 h-1 overflow-hidden rounded-full bg-hairline">
        <span className="block h-full" style={{ width: `${pct}%`, background: `rgb(var(--${tone}))` }} />
      </div>
    </li>
  );
}
