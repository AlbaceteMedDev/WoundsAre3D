import { AppShell } from "@/components/portal/AppShell";
import { getSession } from "@/lib/auth";

const HEAT = [
  ["low", "low", "low", "med", "low"],
  ["low", "low", "low", "low", "low"],
  ["low", "med", "high", "med", "low"],
  ["low", "low", "med", "med", "low"],
  ["low", "low", "low", "low", "low"],
] as const;

const TOP_RISK = [
  { name: "Linda Hayes",     score: 78, reason: "Arterial · denial-prone payer" },
  { name: "Margaret Chen",   score: 71, reason: "Sacral PI stage 3 · stalled 28d" },
  { name: "Sandra Cole",     score: 65, reason: "Missing MN narrative on AO-287" },
  { name: "Walter Klein",    score: 58, reason: "Discharge note pending 4d" },
];

const COMPLIANCE_DAYS = [
  { label: "Notes signed within 48h", pct: 97, change: "+1.4pp" },
  { label: "Photos attached",          pct: 99, change: "+0.6pp" },
  { label: "UDI logged at point-of-care", pct: 100, change: "0pp" },
  { label: "MN narrative complete",    pct: 89, change: "−2.1pp" },
];

const RECENT_REVIEWS = [
  { period: "Apr 2026",  scope: "Internal audit · 24 cases",       result: "All pass" },
  { period: "Q1 2026",   scope: "Payer audit (Medicare)",          result: "0 findings" },
  { period: "Mar 2026",  scope: "Internal audit · 18 cases",       result: "1 minor (corrected)" },
];

const ACTION_ITEMS = [
  { who: "Dr. Morgan",  item: "Sign 2 progression notes (P. Johnson, T. Briggs)", due: "today" },
  { who: "Dr. Romero",  item: "Add MN narrative to CLM-2026-00513",               due: "by Fri" },
  { who: "NP Adler",    item: "Review 1 photo evidence flag",                     due: "today" },
];

export default async function CompliancePage() {
  const session = await getSession();
  return (
    <AppShell
      title="Compliance"
      subtitle="Audit readiness, documentation integrity, reimbursement confidence"
      user={{ name: "Dr. Rachel Morgan", role: session?.role ?? "clinician" }}
    >
      <section className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <Score label="Compliance" value={96} tone="success" sub="audit-ready" />
        <Score label="Audit risk" value={4}  tone="success" sub="lower is better" />
        <Score label="Photo evidence" value={94} tone="success" />
        <Score label="Signature timeliness" value={91} tone="accent" />
        <Score label="LCD adherence" value={95} tone="accent" />
        <Score label="Coding alignment" value={98} tone="success" />
      </section>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <section className="card p-4">
          <span className="eyebrow">Pre-audit checklist</span>
          <h2 className="mt-1 font-display text-base font-semibold text-ink">Across all open cases</h2>
          <ul className="mt-3 space-y-1.5 text-sm">
            {[
              ["HCPCS verification per product / payer",                 "pass"],
              ["LCD/NCD coverage alignment",                             "pass"],
              ["Benefit verification before treatment",                  "pass"],
              ["Photo + 3D evidence attached",                           "pass"],
              ["Operative note signed within 48h",                       "warn"],
              ["UDI / serial / lot recorded",                            "pass"],
              ["Medical necessity narrative present",                    "warn"],
              ["Conservative care 30+ days documented",                  "pass"],
              ["Wagner / DFU staging documented",                        "pass"],
              ["Q-code ASP+6% snapshot stored",                          "pass"],
            ].map(([label, state], i) => (
              <li key={i} className="flex items-center justify-between rounded-md border border-hairline bg-surface px-3 py-2">
                <span className="text-ink-soft">{label}</span>
                <span className={`pill ${state === "pass" ? "pill-success" : "pill-warn"}`}>
                  {state === "pass" ? "PASS" : "REVIEW"}
                </span>
              </li>
            ))}
          </ul>
        </section>

        <section className="card p-4">
          <span className="eyebrow">AI audit-exposure heatmap</span>
          <h2 className="mt-1 font-display text-base font-semibold text-ink">By visit × week</h2>
          <p className="text-xs text-ink-muted">Red cells = clusters likely to attract a payer audit.</p>
          <div className="mt-3 grid grid-cols-5 gap-1">
            {HEAT.flatMap((row, ri) =>
              row.map((cell, ci) => (
                <div
                  key={`${ri}-${ci}`}
                  className={`aspect-square rounded ${
                    cell === "high"
                      ? "bg-danger/70"
                      : cell === "med"
                        ? "bg-warn/60"
                        : "bg-success/15"
                  }`}
                  title={`Risk: ${cell}`}
                />
              )),
            )}
          </div>
          <ul className="mt-3 flex justify-between text-[10px] text-ink-muted">
            <li>W-12</li>
            <li>W-9</li>
            <li>W-6</li>
            <li>W-3</li>
            <li>now</li>
          </ul>
          <div className="mt-3 grid grid-cols-3 gap-2 text-center text-[11px]">
            <Cell tone="success" label="Low" pct={84} />
            <Cell tone="warn" label="Medium" pct={11} />
            <Cell tone="danger" label="High" pct={5} />
          </div>
        </section>

        <section className="card p-4">
          <span className="eyebrow">Top risk patients</span>
          <h2 className="mt-1 font-display text-base font-semibold text-ink">Likely to need attention</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {TOP_RISK.map((r, i) => (
              <li key={i} className="rounded-md border border-hairline bg-surface p-3">
                <div className="flex items-baseline justify-between">
                  <span className="font-medium text-ink">{r.name}</span>
                  <span className={`pill ${r.score >= 70 ? "pill-danger" : r.score >= 60 ? "pill-warn" : "pill-accent"}`}>
                    {r.score}
                  </span>
                </div>
                <p className="mt-0.5 text-[11px] text-ink-muted">{r.reason}</p>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <section className="card p-4">
          <span className="eyebrow">Compliance summary</span>
          <h2 className="mt-1 font-display text-base font-semibold text-ink">Last 30 days</h2>
          <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs">
            <Mini label="Pass actions" value="138" tone="success" />
            <Mini label="Warnings" value="9" tone="warn" />
            <Mini label="Escalations" value="2" tone="danger" />
            <Mini label="Auto-fixed" value="42" tone="accent" />
          </div>
          <ul className="mt-3 space-y-1.5 text-xs">
            {COMPLIANCE_DAYS.map((c) => (
              <li key={c.label}>
                <div className="flex justify-between">
                  <span className="text-ink-soft">{c.label}</span>
                  <span className="tabular-nums text-ink">{c.pct}%</span>
                </div>
                <div className="mt-1 h-1 overflow-hidden rounded-full bg-hairline">
                  <span
                    className="block h-full"
                    style={{
                      width: `${c.pct}%`,
                      background: c.pct >= 95 ? "rgb(var(--success))" : c.pct >= 90 ? "rgb(var(--accent))" : "rgb(var(--warn))",
                    }}
                  />
                </div>
                <p className="text-[10px] text-ink-muted">{c.change}</p>
              </li>
            ))}
          </ul>
        </section>

        <section className="card p-4">
          <span className="eyebrow">Action items</span>
          <h2 className="mt-1 font-display text-base font-semibold text-ink">Open</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {ACTION_ITEMS.map((a, i) => (
              <li key={i} className="rounded-md border border-hairline bg-surface p-3">
                <div className="text-ink">{a.item}</div>
                <div className="mt-1 flex items-center justify-between text-[11px] text-ink-muted">
                  <span>{a.who}</span>
                  <span className={`pill ${a.due === "today" ? "pill-warn" : "pill-neutral"}`}>{a.due}</span>
                </div>
              </li>
            ))}
          </ul>
          <button className="btn btn-primary mt-3 w-full justify-center">Take action</button>
        </section>

        <section className="card p-4">
          <span className="eyebrow">Recent reviews</span>
          <h2 className="mt-1 font-display text-base font-semibold text-ink">Last 90 days</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {RECENT_REVIEWS.map((r, i) => (
              <li key={i} className="rounded-md border border-hairline bg-surface p-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-ink">{r.period}</span>
                  <span className="pill pill-success">{r.result}</span>
                </div>
                <div className="mt-1 text-xs text-ink-muted">{r.scope}</div>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section className="mt-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <Footer label="Chain of custody" value="100%" tone="success" />
        <Footer label="Audit-ready bundle" value="89.6%" tone="accent" />
        <Footer label="Breach notification readiness" value="97%" tone="success" />
        <Footer label="Document match" value="99%" tone="success" />
      </section>
    </AppShell>
  );
}

function Score({ label, value, tone, sub }: { label: string; value: number; tone: "success" | "accent"; sub?: string }) {
  const fill = `rgb(var(--${tone}))`;
  return (
    <div className="card flex flex-col items-center p-4 text-center">
      <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-muted">{label}</div>
      <div
        className="mt-3 grid h-[88px] w-[88px] place-items-center rounded-full"
        style={{
          background: `conic-gradient(${fill} ${value * 3.6}deg, rgb(var(--hairline)) 0)`,
        }}
      >
        <div className="grid h-[72px] w-[72px] place-items-center rounded-full bg-surface">
          <span className="font-display text-xl font-bold text-ink">{value}%</span>
        </div>
      </div>
      {sub && <p className="mt-1 text-[10px] text-ink-muted">{sub}</p>}
    </div>
  );
}

function Mini({ label, value, tone }: { label: string; value: string; tone: "success" | "accent" | "warn" | "danger" }) {
  const cls = `text-${tone}`;
  return (
    <div className="rounded border border-hairline bg-surface-2 p-2 text-center">
      <div className="text-[10px] uppercase tracking-[0.14em] text-ink-muted">{label}</div>
      <div className={`mt-0.5 font-display text-lg font-semibold ${cls}`}>{value}</div>
    </div>
  );
}

function Cell({ tone, label, pct }: { tone: "success" | "warn" | "danger"; label: string; pct: number }) {
  return (
    <div className={`rounded border border-${tone}/40 bg-${tone}/10 p-2`}>
      <div className={`text-[10px] uppercase tracking-[0.14em] text-${tone}`}>{label}</div>
      <div className="mt-0.5 font-display text-base font-semibold text-ink">{pct}%</div>
    </div>
  );
}

function Footer({ label, value, tone }: { label: string; value: string; tone: "success" | "accent" }) {
  return (
    <div className="card p-4">
      <div className="text-[11px] uppercase tracking-[0.14em] text-ink-muted">{label}</div>
      <div className={`mt-2 font-display text-2xl font-semibold ${tone === "success" ? "text-success" : "text-accent"}`}>
        {value}
      </div>
    </div>
  );
}
