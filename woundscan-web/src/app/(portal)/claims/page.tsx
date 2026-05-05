import { AppShell } from "@/components/portal/AppShell";
import { getSession } from "@/lib/auth";
import { CLAIMS, REIMBURSEMENT_TREND } from "@/lib/sample";
import { fmtDate, money } from "@/lib/format";
import { KpiTile } from "@/components/portal/KpiTile";
import { Donut } from "@/components/portal/Donut";
import { Sparkline } from "@/components/portal/Sparkline";

const DENIAL_REASONS = [
  { code: "CO-50", reason: "Medical necessity", count: 4 },
  { code: "CO-16", reason: "Missing/invalid info", count: 2 },
  { code: "CO-97", reason: "Bundled service", count: 2 },
  { code: "CO-22", reason: "Coordination of benefits", count: 1 },
];

export default async function ClaimsPage() {
  const session = await getSession();
  return (
    <AppShell
      title="Claims"
      subtitle="Track reimbursement outcomes and manage claim lifecycle"
      user={{ name: "Dr. Rachel Morgan", role: session?.role ?? "clinician" }}
    >
      <section className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-5">
        <KpiTile label="Paid (mo)" value="78" delta="+12 vs Mar" tone="success" />
        <KpiTile label="Pending" value="9" delta="3 over 30 days" tone="warn" />
        <KpiTile label="Denied" value="2" delta="-3 vs Mar" tone="success" />
        <KpiTile label="Avg days to pay" value="14.2" delta="-2.1 days" tone="accent" />
        <KpiTile label="Total reimbursement" value={money(337_120)} delta="+13% MoM" tone="accent" />
      </section>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-[1fr_360px]">
        <div className="card overflow-hidden">
          <div className="flex items-center justify-between border-b border-hairline bg-surface-2 px-4 py-3 text-xs">
            <div className="flex gap-1.5">
              <Chip active>All ({CLAIMS.length})</Chip>
              <Chip>Paid (3)</Chip>
              <Chip>Pending (2)</Chip>
              <Chip>Denied (1)</Chip>
              <Chip>Appeal (1)</Chip>
            </div>
            <button className="btn btn-secondary">Export 837P</button>
          </div>
          <div className="overflow-x-auto">
            <table className="table-base">
              <thead>
                <tr>
                  <th>Claim</th>
                  <th>Patient</th>
                  <th>CPT</th>
                  <th className="text-right">Submitted</th>
                  <th className="text-right">Allowed</th>
                  <th className="text-right">Paid</th>
                  <th>Status</th>
                  <th>Payer</th>
                </tr>
              </thead>
              <tbody>
                {CLAIMS.map((c) => (
                  <tr key={c.id} className="hover:bg-surface-2">
                    <td className="font-mono text-xs">{c.id}</td>
                    <td>{c.patient}</td>
                    <td className="font-mono text-xs">{c.cpt}</td>
                    <td className="whitespace-nowrap text-right text-ink-muted">{fmtDate(c.submitted)}</td>
                    <td className="text-right tabular-nums">{money(c.amount)}</td>
                    <td className="text-right tabular-nums">
                      {c.paid !== null ? money(c.paid) : "—"}
                    </td>
                    <td><ClaimPill status={c.status} /></td>
                    <td className="text-ink-muted">{c.payer}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="grid grid-cols-1 gap-4 border-t border-hairline p-4 md:grid-cols-3">
            <div className="card p-3">
              <span className="eyebrow">Claims mix</span>
              <div className="mt-2 flex items-center gap-3">
                <Donut
                  size={100}
                  segments={[
                    { value: 78, color: "rgb(var(--success))" },
                    { value: 9, color: "rgb(var(--accent))" },
                    { value: 2, color: "rgb(var(--danger))" },
                    { value: 1, color: "rgb(var(--warn))" },
                  ]}
                  centerLabel="90%"
                  centerSub="paid rate"
                />
                <ul className="space-y-1 text-[11px]">
                  <Legend color="rgb(var(--success))" label="Paid" pct={87} />
                  <Legend color="rgb(var(--accent))" label="Pending" pct={10} />
                  <Legend color="rgb(var(--danger))" label="Denied" pct={2} />
                  <Legend color="rgb(var(--warn))" label="Appeal" pct={1} />
                </ul>
              </div>
            </div>

            <div className="card p-3 md:col-span-2">
              <span className="eyebrow">Reimbursement trend</span>
              <h3 className="mt-1 text-sm font-medium text-ink">Allowed amount per month</h3>
              <Sparkline
                data={REIMBURSEMENT_TREND.map((p, i) => ({ x: i, y: p.paid / 1000, label: p.mo }))}
                height={120}
              />
              <p className="text-[11px] text-ink-muted">y-axis in $K</p>
            </div>
          </div>
        </div>

        <ClaimDetail />
      </div>

      <section className="card mt-6 p-4">
        <span className="eyebrow">Top denial reasons</span>
        <h3 className="mt-1 font-display text-base font-semibold text-ink">By CARC code</h3>
        <ul className="mt-3 grid gap-2 md:grid-cols-2">
          {DENIAL_REASONS.map((d) => (
            <li
              key={d.code}
              className="flex items-center justify-between rounded-md border border-hairline bg-surface px-3 py-2 text-sm"
            >
              <span>
                <span className="font-mono text-xs text-ink-muted">{d.code}</span>
                <span className="ml-2 text-ink">{d.reason}</span>
              </span>
              <span className="pill pill-danger">{d.count}</span>
            </li>
          ))}
        </ul>
      </section>
    </AppShell>
  );
}

function Chip({ children, active }: { children: React.ReactNode; active?: boolean }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-medium ${
        active ? "bg-accent/15 text-accent" : "border border-hairline text-ink-soft"
      }`}
    >
      {children}
    </span>
  );
}

function ClaimPill({ status }: { status: "paid" | "pending" | "denied" | "appeal" }) {
  const map = { paid: "pill pill-success", pending: "pill pill-accent", denied: "pill pill-danger", appeal: "pill pill-warn" };
  return <span className={map[status]}>{status}</span>;
}

function Legend({ color, label, pct }: { color: string; label: string; pct: number }) {
  return (
    <li className="flex items-center justify-between text-ink-soft">
      <span className="flex items-center gap-2">
        <span className="inline-block h-2 w-2 rounded-full" style={{ background: color }} />
        {label}
      </span>
      <span className="tabular-nums text-ink-muted">{pct}%</span>
    </li>
  );
}

function ClaimDetail() {
  return (
    <aside className="card flex flex-col gap-3 p-4">
      <header>
        <span className="eyebrow">Claim detail</span>
        <h2 className="mt-1 font-display text-base font-semibold text-ink">CLM-2026-00517</h2>
        <p className="text-xs text-ink-muted">Patricia Johnson · Medicare A/B</p>
      </header>

      <ul className="space-y-1 text-xs">
        <Row label="Service date" value="Apr 09, 2026" />
        <Row label="Submitted" value="Apr 09, 2026" />
        <Row label="Adjudicated" value="Apr 22, 2026" />
        <Row label="Days to pay" value="13 days" />
        <Row label="CPT" value="15271" />
        <Row label="Q-code" value="A2005" />
        <Row label="Allowed" value={money(1840)} />
        <Row label="Paid" value={money(1727.65)} bold />
      </ul>

      <div className="rounded-md border border-success/40 bg-success/10 p-3 text-xs text-success">
        Paid in full within Medicare timeline.
      </div>

      <div className="mt-2">
        <p className="text-[11px] uppercase tracking-[0.14em] text-ink-muted">
          Linked artifacts
        </p>
        <ul className="mt-1.5 space-y-1 text-xs">
          <li className="flex justify-between"><span>Progression note</span><a className="text-accent hover:text-accent-bright" href="#">view ↗</a></li>
          <li className="flex justify-between"><span>3D scan record</span><a className="text-accent hover:text-accent-bright" href="#">view ↗</a></li>
          <li className="flex justify-between"><span>UDI graft application</span><a className="text-accent hover:text-accent-bright" href="#">view ↗</a></li>
          <li className="flex justify-between"><span>Pre-submission audit log</span><a className="text-accent hover:text-accent-bright" href="#">view ↗</a></li>
        </ul>
      </div>

      <button className="btn btn-secondary mt-auto justify-center">Start correction</button>
    </aside>
  );
}

function Row({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <li className={`flex justify-between ${bold ? "border-t border-hairline pt-1.5 font-semibold text-ink" : "text-ink-soft"}`}>
      <span>{label}</span>
      <span className="tabular-nums">{value}</span>
    </li>
  );
}
