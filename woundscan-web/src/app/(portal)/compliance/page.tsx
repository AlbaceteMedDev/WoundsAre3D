import { AppShell } from "@/components/portal/AppShell";
import { getSession } from "@/lib/auth";

const CHECKLIST = [
  { item: "HCPCS verification per product / payer", state: "pass" },
  { item: "LCD/NCD coverage alignment", state: "pass" },
  { item: "Benefit verification before treatment", state: "pass" },
  { item: "Photo + 3D evidence attached", state: "pass" },
  { item: "Operative note signed within 48h", state: "warn" },
  { item: "UDI / serial / lot recorded", state: "pass" },
  { item: "Medical necessity narrative present", state: "warn" },
  { item: "Conservative care 30+ days documented", state: "pass" },
  { item: "Wagner / DFU staging documented", state: "pass" },
  { item: "Q-code ASP+6% snapshot stored", state: "pass" },
];

const ACTIONS = [
  { who: "Dr. Morgan", item: "Sign 2 progression notes (P. Johnson, T. Briggs)", due: "today" },
  { who: "Dr. Romero", item: "Add MN narrative to CLM-2026-00513", due: "by Fri" },
  { who: "NP Adler", item: "Review 1 photo evidence flag", due: "today" },
];

const EXCEPTIONS = [
  { at: "Apr 25", who: "Dr. Romero", what: "Note signed at 73h (target 48h)", severity: "low" },
  { at: "Apr 22", who: "Billing", what: "CO-50 denial — added MN narrative on appeal", severity: "med" },
  { at: "Apr 18", who: "Audit", what: "Photo missing — captured retroactively", severity: "low" },
];

const REVIEWS = [
  { period: "Apr 2026", scope: "Internal audit · 24 cases", result: "All pass" },
  { period: "Q1 2026", scope: "Payer audit (Medicare)", result: "0 findings" },
  { period: "Mar 2026", scope: "Internal audit · 18 cases", result: "1 minor (corrected)" },
];

export default async function CompliancePage() {
  const session = await getSession();
  return (
    <AppShell
      title="Compliance"
      subtitle="Audit readiness, documentation integrity, reimbursement confidence"
      user={{ name: "Dr. Rachel Morgan", role: session?.role ?? "clinician" }}
    >
      <section className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
        <Score label="Compliance" value={96} tone="success" />
        <Score label="Audit readiness" value={98} tone="success" />
        <Score label="HCPCS verification" value={98} tone="success" />
        <Score label="LCD / NCD alignment" value={95} tone="accent" />
        <Score label="MN narrative" value={93} tone="accent" />
        <Score label="Benefit verification" value={97} tone="success" />
      </section>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <section className="card p-4">
          <span className="eyebrow">Pre-audit checklist</span>
          <h2 className="mt-1 font-display text-base font-semibold text-ink">Across all open cases</h2>
          <ul className="mt-3 space-y-1.5 text-sm">
            {CHECKLIST.map((c, i) => (
              <li key={i} className="flex items-center justify-between rounded-md border border-hairline bg-surface px-3 py-2">
                <span className="text-ink-soft">{c.item}</span>
                <span className={`pill ${c.state === "pass" ? "pill-success" : "pill-warn"}`}>
                  {c.state === "pass" ? "PASS" : "REVIEW"}
                </span>
              </li>
            ))}
          </ul>
          <button className="btn btn-secondary mt-3 w-full justify-center">View Full Checklist</button>
        </section>

        <section className="card p-4">
          <span className="eyebrow">Clinician action items</span>
          <h2 className="mt-1 font-display text-base font-semibold text-ink">Open</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {ACTIONS.map((a, i) => (
              <li key={i} className="rounded-md border border-hairline bg-surface p-3">
                <div className="text-ink">{a.item}</div>
                <div className="mt-1 flex items-center justify-between text-[11px] text-ink-muted">
                  <span>{a.who}</span>
                  <span className={`pill ${a.due === "today" ? "pill-warn" : "pill-neutral"}`}>{a.due}</span>
                </div>
              </li>
            ))}
          </ul>
          <button className="btn btn-primary mt-3 w-full justify-center">Take Action</button>
        </section>

        <section className="card p-4">
          <span className="eyebrow">Recent compliance reviews</span>
          <h2 className="mt-1 font-display text-base font-semibold text-ink">Last 90 days</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {REVIEWS.map((r, i) => (
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

      <section className="card mt-6 p-4">
        <span className="eyebrow">Exception log</span>
        <h2 className="mt-1 font-display text-base font-semibold text-ink">Last 30 days</h2>
        <table className="table-base mt-3">
          <thead>
            <tr>
              <th>Date</th>
              <th>Who</th>
              <th>Event</th>
              <th>Severity</th>
            </tr>
          </thead>
          <tbody>
            {EXCEPTIONS.map((e, i) => (
              <tr key={i}>
                <td className="whitespace-nowrap">{e.at}</td>
                <td>{e.who}</td>
                <td>{e.what}</td>
                <td>
                  <span className={`pill ${e.severity === "med" ? "pill-warn" : "pill-neutral"}`}>
                    {e.severity}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </AppShell>
  );
}

function Score({ label, value, tone }: { label: string; value: number; tone: "success" | "accent" }) {
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
    </div>
  );
}
