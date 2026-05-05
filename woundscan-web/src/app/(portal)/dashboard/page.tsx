import Link from "next/link";
import { AppShell } from "@/components/portal/AppShell";
import { getSession } from "@/lib/auth";
import { ACTIVITY, HEALING_TREND, VOLUME_TREND } from "@/lib/sample";
import { money } from "@/lib/format";
import { KpiTile } from "@/components/portal/KpiTile";
import { Sparkline } from "@/components/portal/Sparkline";
import { Donut } from "@/components/portal/Donut";

export default async function DashboardPage() {
  const session = await getSession();
  return (
    <AppShell
      title="Clinical Operating Dashboard"
      subtitle="Audit-ready by design"
      user={{ name: "Dr. Rachel Morgan", role: session?.role ?? "clinician" }}
    >
      <section className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-5">
        <KpiTile label="Active patients" value="18" delta="+3 this week" tone="accent" />
        <KpiTile label="Seen this week" value="7" delta="+2 vs avg" />
        <KpiTile label="Scans this week" value="64" delta="+18%" tone="accent" />
        <KpiTile label="High-risk" value="5" delta="2 unaddressed" tone="warn" />
        <KpiTile label="Pending orders" value="12" delta="3 over 48h" tone="warn" />
      </section>

      <section className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="card p-4 lg:col-span-2">
          <div className="flex items-baseline justify-between">
            <div>
              <span className="eyebrow">Wound healing trend</span>
              <h2 className="mt-1 font-display text-base font-semibold text-ink">
                Mean area reduction · cm² / week
              </h2>
            </div>
            <span className="text-xs text-ink-muted">last 8 weeks</span>
          </div>
          <div className="mt-4">
            <Sparkline
              data={HEALING_TREND.map((p, i) => ({ x: i, label: p.week, y: p.actual }))}
              targetLine={1.6}
              height={180}
            />
          </div>
          <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
            <Mini label="Avg / wk" value="2.05 cm²" />
            <Mini label="Best week" value="2.6 cm²" />
            <Mini label="Stalled wounds" value="2 / 18" tone="warn" />
          </div>
        </div>

        <div className="card flex flex-col p-4">
          <span className="eyebrow">Reimbursement</span>
          <h2 className="mt-1 font-display text-base font-semibold text-ink">
            April allowed amount
          </h2>
          <p className="mt-2 font-display text-3xl font-semibold text-ink">{money(337_120)}</p>
          <p className="text-xs text-success">+13% vs March</p>
          <div className="mt-3 space-y-1.5 text-xs">
            <Row label="Paid" value={money(298_400)} pct={88.5} tone="success" />
            <Row label="Pending" value={money(34_120)} pct={10.1} tone="accent" />
            <Row label="Denied" value={money(4_600)} pct={1.4} tone="danger" />
          </div>
          <Link href="/claims" className="btn btn-secondary mt-auto justify-center">
            View claims →
          </Link>
        </div>
      </section>

      <section className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="card p-4">
          <span className="eyebrow">Healing progress</span>
          <h2 className="mt-1 font-display text-base font-semibold text-ink">By outcome bucket</h2>
          <div className="mt-3 flex items-center gap-4">
            <Donut
              size={130}
              segments={[
                { value: 38, color: "rgb(var(--success))", label: "Healing on track" },
                { value: 33, color: "rgb(var(--accent))", label: "Tracking" },
                { value: 18, color: "rgb(var(--warn))", label: "Stalled" },
                { value: 11, color: "rgb(var(--danger))", label: "Worsening" },
              ]}
            />
            <ul className="space-y-1 text-xs">
              <Legend color="rgb(var(--success))" label="On track" pct={38} />
              <Legend color="rgb(var(--accent))" label="Tracking" pct={33} />
              <Legend color="rgb(var(--warn))" label="Stalled" pct={18} />
              <Legend color="rgb(var(--danger))" label="Worsening" pct={11} />
            </ul>
          </div>
        </div>

        <div className="card p-4">
          <span className="eyebrow">Scan volume</span>
          <h2 className="mt-1 font-display text-base font-semibold text-ink">This week</h2>
          <div className="mt-3 flex items-end gap-2 h-[140px]">
            {VOLUME_TREND.map((d) => (
              <div key={d.day} className="flex flex-1 flex-col items-center justify-end">
                <div
                  className="w-full rounded-t bg-accent/70"
                  style={{ height: `${(d.scans / 16) * 100}%` }}
                />
                <span className="mt-1 text-[10px] text-ink-muted">{d.day}</span>
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs text-ink-muted">Peak: Friday · 16 scans</p>
        </div>

        <div className="card p-4">
          <span className="eyebrow">Compliance scorecard</span>
          <h2 className="mt-1 font-display text-base font-semibold text-ink">Audit readiness</h2>
          <div className="mt-3 flex items-center gap-4">
            <div className="grid h-[110px] w-[110px] place-items-center rounded-full border-[6px] border-success/30" style={{ borderTopColor: "rgb(var(--success))", borderRightColor: "rgb(var(--success))", transform: "rotate(-45deg)" }}>
              <span className="font-display text-3xl font-bold text-ink" style={{ transform: "rotate(45deg)" }}>96%</span>
            </div>
            <ul className="flex-1 space-y-1.5 text-xs">
              <Compliance label="HCPCS verified" pct={98} />
              <Compliance label="LCD/NCD aligned" pct={95} />
              <Compliance label="Photo evidence" pct={93} />
              <Compliance label="Signed within 48h" pct={97} />
            </ul>
          </div>
        </div>
      </section>

      <section className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="card p-4 lg:col-span-2">
          <header className="flex items-baseline justify-between">
            <div>
              <span className="eyebrow">Activity</span>
              <h2 className="mt-1 font-display text-base font-semibold text-ink">
                Recent across the practice
              </h2>
            </div>
            <Link href="/notes" className="text-xs text-accent hover:text-accent-bright">
              All activity →
            </Link>
          </header>
          <ul className="mt-3 divide-y divide-hairline">
            {ACTIVITY.map((a, i) => (
              <li key={i} className="flex items-center gap-3 py-2 text-sm">
                <span className="font-mono text-[11px] text-ink-muted">{a.at}</span>
                <span className="font-medium text-ink">{a.who}</span>
                <span className="text-ink-soft">{a.what}</span>
                <span className="ml-auto truncate text-ink-muted">{a.subject}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="card flex flex-col p-4">
          <span className="eyebrow">Quick actions</span>
          <div className="mt-3 grid grid-cols-1 gap-2">
            <QuickAction href="/wounds" label="Open 3D wound analysis" />
            <QuickAction href="/notes" label="Draft audit-safe note" />
            <QuickAction href="/orders" label="Place an order" />
            <QuickAction href="/claims" label="Submit a claim" />
            <QuickAction href="/reports" label="Generate report" />
          </div>
        </div>
      </section>
    </AppShell>
  );
}

function Mini({ label, value, tone }: { label: string; value: string; tone?: "warn" }) {
  return (
    <div className={`rounded border border-hairline bg-surface-2 px-3 py-2 ${tone === "warn" ? "border-warn/40" : ""}`}>
      <div className="text-[10px] uppercase tracking-[0.14em] text-ink-muted">{label}</div>
      <div className={`mt-0.5 font-display text-sm font-semibold ${tone === "warn" ? "text-warn" : "text-ink"}`}>
        {value}
      </div>
    </div>
  );
}

function Row({ label, value, pct, tone }: { label: string; value: string; pct: number; tone: "success" | "accent" | "danger" }) {
  const fill = `rgb(var(--${tone}))`;
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-ink-soft">{label}</span>
        <span className="font-medium text-ink">{value}</span>
      </div>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-hairline">
        <span className="block h-full" style={{ width: `${pct}%`, background: fill }} />
      </div>
    </div>
  );
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

function Compliance({ label, pct }: { label: string; pct: number }) {
  return (
    <li>
      <div className="flex justify-between">
        <span className="text-ink-soft">{label}</span>
        <span className="tabular-nums text-ink">{pct}%</span>
      </div>
      <div className="mt-1 h-1 overflow-hidden rounded-full bg-hairline">
        <span className="block h-full bg-success" style={{ width: `${pct}%` }} />
      </div>
    </li>
  );
}

function QuickAction({ href, label }: { href: string; label: string }) {
  return (
    <Link
      href={href}
      className="flex items-center justify-between rounded-md border border-hairline bg-surface px-3 py-2 text-sm text-ink-soft transition hover:border-accent/50 hover:bg-surface-2 hover:text-ink"
    >
      <span>{label}</span>
      <span className="text-accent">→</span>
    </Link>
  );
}
