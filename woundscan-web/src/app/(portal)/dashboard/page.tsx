import Link from "next/link";
import { AppShell } from "@/components/portal/AppShell";
import { getSession } from "@/lib/auth";
import { ACTIVITY, HEALING_TREND, VOLUME_TREND } from "@/lib/sample";
import { money } from "@/lib/format";
import { KpiTile } from "@/components/portal/KpiTile";
import { Sparkline } from "@/components/portal/Sparkline";
import { Donut } from "@/components/portal/Donut";

const TODAY_VISITS = [
  { time: "08:30", who: "Patricia Johnson",  what: "Wound check + ActiGraft+ q14d",   status: "complete" },
  { time: "09:25", who: "James Carter",      what: "Surgical follow-up",               status: "complete" },
  { time: "10:20", who: "Robert Williams",   what: "VLU compression check",            status: "next" },
  { time: "11:30", who: "Margaret Chen",     what: "Sacral PI · debridement",          status: "scheduled" },
  { time: "13:15", who: "Sandra Cole",       what: "DFU dressing change",              status: "scheduled" },
  { time: "14:25", who: "Carlos Reyes",      what: "VLU follow-up",                    status: "scheduled" },
  { time: "15:30", who: "Linda Hayes",       what: "Arterial reassessment + photo",    status: "delay" },
  { time: "16:35", who: "Helen Park",        what: "Heel offloading review",           status: "scheduled" },
] as const;

export default async function DashboardPage() {
  const session = await getSession();
  return (
    <AppShell
      title="Clinical Operating Dashboard"
      subtitle="Audit-ready by design · Tuesday, May 12, 2026"
      user={{ name: "Dr. Rachel Morgan", role: session?.role ?? "clinician" }}
    >
      {/* TOP KPI ROW */}
      <section className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <KpiTile label="Today's patients" value="5" delta="3 home · 2 clinic" tone="accent" />
        <KpiTile label="Active patients" value="128" delta="+12 this week" tone="accent" />
        <KpiTile label="Excellent cases" value="12" delta="≥80% closure" tone="success" />
        <KpiTile label="High-risk" value="5" delta="2 unaddressed" tone="warn" />
        <KpiTile label="Pending orders" value="12" delta="3 over 48h" tone="warn" />
        <KpiTile label="Stalled wounds" value="3" delta="age >21d" tone="warn" />
      </section>

      <section className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-7">
        <MiniStat label="42.6 mi" desc="route distance" />
        <MiniStat label="18.3 mi" desc="completed today" />
        <MiniStat label="19" desc="scans this week" />
        <MiniStat label="34.2%" desc="mean area reduction" tone="success" />
        <MiniStat label="68.3%" desc="healing rate (90d)" tone="success" />
        <MiniStat label="14.2d" desc="avg days to pay" tone="accent" />
        <MiniStat label="96%" desc="compliance score" tone="success" />
      </section>

      {/* MAIN GRID */}
      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-[1fr_320px]">
        <div className="space-y-4">
          {/* Healing velocity bands */}
          <div className="card p-4">
            <div className="flex items-baseline justify-between">
              <div>
                <span className="eyebrow">Healing velocity bands</span>
                <h2 className="mt-1 font-display text-base font-semibold text-ink">
                  Mean area reduction · cm² / week
                </h2>
              </div>
              <span className="text-xs text-ink-muted">last 8 weeks · against target 1.6 cm²/wk</span>
            </div>
            <Sparkline
              data={HEALING_TREND.map((p, i) => ({ x: i, label: p.week, y: p.actual }))}
              targetLine={1.6}
              height={200}
            />
            <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
              <Mini label="Avg / wk" value="2.05 cm²" />
              <Mini label="Best week" value="2.6 cm²" />
              <Mini label="Stalled" value="2 / 18" tone="warn" />
            </div>
          </div>

          {/* 3-up: healing donut, scan volume, compliance */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="card p-4">
              <span className="eyebrow">Healing progress</span>
              <h3 className="mt-1 font-display text-sm font-semibold text-ink">By outcome bucket</h3>
              <div className="mt-3 flex items-center gap-3">
                <Donut
                  size={108}
                  segments={[
                    { value: 38, color: "rgb(var(--success))" },
                    { value: 33, color: "rgb(var(--accent))" },
                    { value: 18, color: "rgb(var(--warn))" },
                    { value: 11, color: "rgb(var(--danger))" },
                  ]}
                  centerLabel="71%"
                  centerSub="positive"
                />
                <ul className="flex-1 space-y-1 text-[11px]">
                  <Legend color="rgb(var(--success))" label="On track" pct={38} />
                  <Legend color="rgb(var(--accent))" label="Tracking" pct={33} />
                  <Legend color="rgb(var(--warn))" label="Stalled" pct={18} />
                  <Legend color="rgb(var(--danger))" label="Worsening" pct={11} />
                </ul>
              </div>
            </div>

            <div className="card p-4">
              <span className="eyebrow">Documentation integrity</span>
              <h3 className="mt-1 font-display text-sm font-semibold text-ink">Audit readiness</h3>
              <div className="mt-3 flex items-center gap-3">
                <div
                  className="grid h-[108px] w-[108px] place-items-center rounded-full"
                  style={{
                    background:
                      "conic-gradient(rgb(var(--success)) 346deg, rgb(var(--hairline)) 0)",
                  }}
                >
                  <div className="grid h-[88px] w-[88px] place-items-center rounded-full bg-surface">
                    <span className="font-display text-2xl font-bold text-ink">96%</span>
                  </div>
                </div>
                <ul className="flex-1 space-y-1.5 text-[11px]">
                  <ScoreRow label="HCPCS" pct={98} />
                  <ScoreRow label="LCD/NCD" pct={95} />
                  <ScoreRow label="Photo" pct={93} />
                  <ScoreRow label="48h sign" pct={97} />
                </ul>
              </div>
            </div>

            <div className="card flex flex-col p-4">
              <span className="eyebrow">Claims &amp; outcomes</span>
              <h3 className="mt-1 font-display text-sm font-semibold text-ink">April reimbursement</h3>
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
          </div>

          {/* Activity */}
          <div className="card p-4">
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

          {/* Scan volume + extra */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="card p-4">
              <span className="eyebrow">Scan volume</span>
              <h3 className="mt-1 font-display text-sm font-semibold text-ink">This week</h3>
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
              <span className="eyebrow">Today's snapshot</span>
              <h3 className="mt-1 font-display text-sm font-semibold text-ink">Operational</h3>
              <ul className="mt-3 grid grid-cols-2 gap-2 text-xs">
                <SnapshotTile label="On time visits" value="6 / 8" tone="accent" />
                <SnapshotTile label="Avg visit length" value="28 min" />
                <SnapshotTile label="Capture quality A/B" value="91%" tone="success" />
                <SnapshotTile label="Photos captured" value="14" />
                <SnapshotTile label="Notes signed" value="7 / 9" tone="warn" />
                <SnapshotTile label="Claims drafted" value="4" />
              </ul>
            </div>
          </div>
        </div>

        {/* RIGHT: Visit schedule */}
        <aside className="card flex flex-col p-4">
          <header className="flex items-center justify-between">
            <div>
              <span className="eyebrow">Visit schedule</span>
              <h2 className="mt-1 font-display text-base font-semibold text-ink">Today · 8 stops</h2>
            </div>
            <Link href="/routes" className="text-xs text-accent hover:text-accent-bright">
              Route →
            </Link>
          </header>
          <ul className="mt-3 space-y-2 text-sm">
            {TODAY_VISITS.map((v) => (
              <li
                key={v.time}
                className={`flex items-start gap-2.5 rounded-md border p-2.5 ${
                  v.status === "next"
                    ? "border-accent/50 bg-accent/5"
                    : v.status === "delay"
                      ? "border-warn/40 bg-warn/5"
                      : v.status === "complete"
                        ? "border-hairline bg-surface-2 opacity-70"
                        : "border-hairline bg-surface"
                }`}
              >
                <span className="font-mono text-[11px] text-ink-muted">{v.time}</span>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-ink">{v.who}</p>
                  <p className="truncate text-[11px] text-ink-muted">{v.what}</p>
                </div>
                {v.status === "complete" && <span className="pill pill-success">✓</span>}
                {v.status === "next" && <span className="pill pill-accent">next</span>}
                {v.status === "delay" && <span className="pill pill-warn">delay</span>}
              </li>
            ))}
          </ul>

          <div className="mt-4 rounded-md border border-hairline bg-surface-2 p-3 text-[11px] text-ink-soft">
            <p className="font-semibold text-ink">Route summary</p>
            <p className="mt-1">42.6 mi · 2h 15m drive · ends 17:00</p>
            <p className="mt-0.5 text-success">94% efficiency vs 86% avg</p>
          </div>
        </aside>
      </div>

      {/* QUICK ACTIONS BAR */}
      <section className="mt-6">
        <span className="eyebrow">Quick actions</span>
        <div className="mt-2 grid grid-cols-2 gap-2 md:grid-cols-3 lg:grid-cols-6">
          <ActionTile href="/wounds" label="Open 3D Scan" icon="◉" />
          <ActionTile href="/notes" label="Audit-Safe Note" icon="✎" />
          <ActionTile href="/orders" label="Add Order" icon="+" />
          <ActionTile href="/routes" label="Optimize Route" icon="↳" />
          <ActionTile href="/inventory" label="Assign Graft" icon="◇" />
          <ActionTile href="/reports" label="Generate Report" icon="≣" />
        </div>
      </section>
    </AppShell>
  );
}

function MiniStat({ label, desc, tone }: { label: string; desc: string; tone?: "accent" | "success" }) {
  const cls = tone === "success" ? "text-success" : tone === "accent" ? "text-accent" : "text-ink";
  return (
    <div className="card flex flex-col items-start p-3">
      <div className={`font-display text-lg font-semibold tabular-nums ${cls}`}>{label}</div>
      <div className="text-[11px] text-ink-muted">{desc}</div>
    </div>
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
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-ink-soft">{label}</span>
        <span className="font-medium text-ink">{value}</span>
      </div>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-hairline">
        <span className="block h-full" style={{ width: `${pct}%`, background: `rgb(var(--${tone}))` }} />
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

function ScoreRow({ label, pct }: { label: string; pct: number }) {
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

function SnapshotTile({ label, value, tone }: { label: string; value: string; tone?: "success" | "accent" | "warn" }) {
  const cls = { success: "text-success", accent: "text-accent", warn: "text-warn" }[tone ?? "success"];
  return (
    <li className="rounded border border-hairline bg-surface-2 p-2">
      <div className="text-[10px] uppercase tracking-[0.14em] text-ink-muted">{label}</div>
      <div className={`mt-1 font-display text-base font-semibold ${tone ? cls : "text-ink"}`}>{value}</div>
    </li>
  );
}

function ActionTile({ href, label, icon }: { href: string; label: string; icon: string }) {
  return (
    <Link
      href={href}
      className="card flex items-center gap-3 p-3 transition hover:border-accent/60 hover:bg-accent/5"
    >
      <span className="grid h-8 w-8 place-items-center rounded-md bg-accent/15 font-display text-accent">
        {icon}
      </span>
      <span className="text-sm font-medium text-ink">{label}</span>
    </Link>
  );
}
