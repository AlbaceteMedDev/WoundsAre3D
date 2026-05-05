import { AppShell } from "@/components/portal/AppShell";
import { getSession } from "@/lib/auth";

const TEMPLATE_TABS = [
  "DFU Follow-Up",
  "Pressure Injury",
  "Venous Leg Ulcer",
  "Surgical Dehiscence",
  "Smart Insert",
  "Policy & LCD Alignment",
];

const RECENT_DOCS = [
  { name: "Note · P. Johnson · v6", at: "today 09:34", state: "draft" },
  { name: "Note · J. Carter · v3",  at: "today 08:55", state: "signed" },
  { name: "Note · M. Chen · v9",    at: "yesterday",  state: "signed" },
  { name: "Note · S. Cole · v4",    at: "Apr 28",     state: "signed" },
];

export default async function NotesPage() {
  const session = await getSession();
  return (
    <AppShell
      title="Audit-Safe Notes"
      subtitle="Create comprehensive, compliant, and audit-ready clinical documentation"
      user={{ name: "Dr. Rachel Morgan", role: session?.role ?? "clinician" }}
    >
      {/* Template tabs */}
      <nav className="mb-3 flex flex-wrap items-center gap-1.5">
        {TEMPLATE_TABS.map((t, i) => (
          <button
            key={t}
            className={`inline-flex items-center rounded-full px-3 py-1.5 text-xs font-medium transition ${
              i === 0
                ? "bg-accent text-white dark:text-ink"
                : "border border-hairline text-ink-soft hover:border-accent hover:text-accent"
            }`}
          >
            {t}
          </button>
        ))}
        <div className="ml-auto flex gap-2">
          <button className="btn btn-secondary">Use template</button>
          <button className="btn btn-primary">+ New from data</button>
        </div>
      </nav>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_320px]">
        <section className="card overflow-hidden p-0">
          <header className="flex items-center justify-between border-b border-hairline p-4">
            <div>
              <span className="eyebrow">Drafting · DFU follow-up</span>
              <h2 className="mt-1 font-display text-base font-semibold text-ink">
                Patricia Johnson · DFU R plantar 1st MTP · visit 6
              </h2>
              <p className="text-xs text-ink-muted">
                Anchored to measurement Apr 29, 2026 · grade B · auto-saved 14s ago
              </p>
            </div>
            <div className="flex gap-2">
              <button className="btn btn-secondary">Save draft</button>
              <button className="btn btn-primary">Sign &amp; lock</button>
            </div>
          </header>

          <div className="space-y-5 p-5 text-sm leading-relaxed">
            <Group title="Wound type & history">
              <Field label="Wound type" value="Diabetic foot ulcer" />
              <Field label="Onset" value="Feb 06, 2026 (12 weeks)" />
              <Field label="Wagner / depth grade" value="2 / Stage 2" />
              <Field label="Prior treatments" value="Dressings, offloading, ABx (Apr 02–14)" />
            </Group>

            <Group title="Tissue composition (locked from measurement)">
              <table className="table-base">
                <thead>
                  <tr>
                    <th>Tissue</th>
                    <th className="text-right">% surface</th>
                    <th className="text-right">vs prior</th>
                    <th>Notes</th>
                  </tr>
                </thead>
                <tbody>
                  <TissueRow tissue="Granulation" pct={62} delta="+8" tone="success" note="healthy beefy red" />
                  <TissueRow tissue="Slough"      pct={28} delta="−6" tone="success" note="loose, irrigation only" />
                  <TissueRow tissue="Eschar"      pct={10} delta="−2" tone="accent"  note="dry, no tunneling" />
                  <TissueRow tissue="Epithelial"  pct={0}  delta="0"  tone="neutral" note="not yet contracting" />
                </tbody>
              </table>
            </Group>

            <Group title="Tunneling & undermining">
              <div className="grid grid-cols-2 gap-3 text-xs md:grid-cols-4">
                <Cell label="Tunneling" value="None" />
                <Cell label="Undermining 12 o'clock" value="0.4 cm" />
                <Cell label="Undermining 3 o'clock" value="0.2 cm" />
                <Cell label="Undermining 6 o'clock" value="0.0 cm" tone="success" />
                <Cell label="Undermining 9 o'clock" value="0.3 cm" />
                <Cell label="Probe-to-bone" value="Negative" tone="success" />
                <Cell label="Sinus tract" value="None" tone="success" />
                <Cell label="Drainage amount" value="Scant serous" />
              </div>
            </Group>

            <Group title="Subjective findings">
              <p className="text-ink-soft">
                67F with T2DM presents for follow-up of right plantar 1st MTP DFU. Reports
                improved comfort with offloading boot. Denies new drainage, fever, increased pain.
                Adherent to plan.
              </p>
            </Group>

            <Group title="Plan & follow-up">
              <ul className="space-y-1 text-ink-soft">
                <li>· Continue ActiGraft+ q14d, total contact cast change weekly</li>
                <li>· Vascular reassessment in 30 days</li>
                <li>· PCP coordination for A1c</li>
                <li>· RTC 7 days</li>
              </ul>
            </Group>

            <Group title="Procedure">
              <Field label="CPT" value="15271 · primary application up to 100 cm²" />
              <Field label="Q-code" value="A2005 · ActiGraft+ ASP+6%" />
              <Field label="Add-on" value="97597 · debridement (if performed)" />
              <Field label="Applied area" value="14.7 cm² (UDI logged)" />
            </Group>
          </div>
        </section>

        <aside className="space-y-4">
          {/* Audit-Safe Score */}
          <div className="card p-4">
            <span className="eyebrow">Audit-Safe Score</span>
            <div className="mt-3 flex items-center gap-3">
              <div
                className="grid h-[100px] w-[100px] place-items-center rounded-full"
                style={{
                  background:
                    "conic-gradient(rgb(var(--success)) 332deg, rgb(var(--hairline)) 0)",
                }}
              >
                <div className="grid h-[78px] w-[78px] place-items-center rounded-full bg-surface">
                  <span className="font-display text-2xl font-bold text-ink">92%</span>
                </div>
              </div>
              <ul className="flex-1 space-y-1.5 text-[11px]">
                <Score label="Documentation" pct={92} />
                <Score label="Coding" pct={88} />
                <Score label="Photo evidence" pct={95} />
                <Score label="Sign timeliness" pct={75} />
                <Score label="LCD adherence" pct={86} />
              </ul>
            </div>
          </div>

          {/* Documentation checklist */}
          <div className="card p-4">
            <span className="eyebrow">Documentation checklist</span>
            <ul className="mt-2 space-y-1.5 text-xs">
              <Check label="Wound type + Wagner grade documented" />
              <Check label="Measurement attached + locked" />
              <Check label="Tissue composition recorded" />
              <Check label="Tunneling/undermining noted" />
              <Check label="UDI / lot / serial captured" />
              <Check label="Conservative care 30+ days" />
              <Check label="MN narrative drafted" warn />
              <Check label="Photo evidence" />
              <Check label="Coding aligned w/ LCD" />
            </ul>
          </div>

          {/* Patient summary */}
          <div className="card p-4">
            <span className="eyebrow">Patient summary</span>
            <h3 className="mt-1 font-display text-base font-semibold text-ink">Patricia Johnson</h3>
            <p className="text-xs text-ink-muted">67F · MRN-002847 · Medicare A/B</p>
            <ul className="mt-2 space-y-1 text-xs text-ink-soft">
              <li>· DFU R plantar 1st MTP · onset Feb 06</li>
              <li>· Wagner grade 2</li>
              <li>· A1c 7.8 (Mar 2026)</li>
              <li>· ABI 0.91 R / 0.94 L</li>
            </ul>
          </div>

          {/* Recent documents */}
          <div className="card p-4">
            <span className="eyebrow">Recent documents</span>
            <ul className="mt-2 space-y-1.5 text-xs">
              {RECENT_DOCS.map((d, i) => (
                <li key={i} className="flex items-center justify-between rounded-md border border-hairline bg-surface px-3 py-2">
                  <span className="text-ink">{d.name}</span>
                  <span className="flex items-center gap-2">
                    <span className="text-ink-muted">{d.at}</span>
                    <span className={`pill ${d.state === "signed" ? "pill-success" : "pill-warn"}`}>
                      {d.state}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <button className="btn btn-secondary w-full justify-center">Export PDF</button>
        </aside>
      </div>
    </AppShell>
  );
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-accent">
        {title}
      </h3>
      <div className="space-y-2">{children}</div>
    </section>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between border-b border-hairline pb-1.5 last:border-b-0">
      <span className="text-ink-muted">{label}</span>
      <span className="text-ink">{value}</span>
    </div>
  );
}

function Cell({ label, value, tone }: { label: string; value: string; tone?: "success" }) {
  return (
    <div className="rounded border border-hairline bg-surface-2 p-2">
      <div className="text-[10px] uppercase tracking-[0.14em] text-ink-muted">{label}</div>
      <div className={`mt-0.5 font-display text-sm font-semibold ${tone === "success" ? "text-success" : "text-ink"}`}>
        {value}
      </div>
    </div>
  );
}

function TissueRow({ tissue, pct, delta, tone, note }: { tissue: string; pct: number; delta: string; tone: "success" | "accent" | "neutral"; note: string }) {
  const cls = { success: "text-success", accent: "text-accent", neutral: "text-ink-muted" }[tone];
  return (
    <tr>
      <td className="font-medium text-ink">{tissue}</td>
      <td className="text-right tabular-nums">{pct}%</td>
      <td className={`text-right tabular-nums ${cls}`}>{delta}</td>
      <td className="text-ink-muted">{note}</td>
    </tr>
  );
}

function Score({ label, pct }: { label: string; pct: number }) {
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

function Check({ label, warn }: { label: string; warn?: boolean }) {
  return (
    <li className="flex items-start gap-2">
      <span
        className={`mt-0.5 grid h-3 w-3 place-items-center rounded-sm ${
          warn ? "bg-warn/20 text-warn" : "bg-success/20 text-success"
        }`}
      >
        <span className="text-[10px]">✓</span>
      </span>
      <span className={`flex-1 ${warn ? "text-warn" : "text-ink-soft"}`}>{label}</span>
    </li>
  );
}
