import Link from "next/link";
import { AppShell } from "@/components/portal/AppShell";
import { getSession } from "@/lib/auth";
import { PATIENTS } from "@/lib/sample";
import { fmtDate } from "@/lib/format";
import { KpiTile } from "@/components/portal/KpiTile";
import { Sparkline } from "@/components/portal/Sparkline";

export default async function PatientRosterPage() {
  const session = await getSession();
  return (
    <AppShell
      title="Patient Roster"
      subtitle="128 patients · sorted by last seen · audit-ready"
      user={{ name: "Dr. Rachel Morgan", role: session?.role ?? "clinician" }}
    >
      <section className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-8">
        <KpiTile label="Total" value="128" delta="all locations" />
        <KpiTile label="Active" value="32" delta="+4 this week" tone="accent" />
        <KpiTile label="Reassessment" value="34" delta="due ≤30d" tone="accent" />
        <KpiTile label="Discharged" value="18" delta="last 90d" />
        <KpiTile label="High-risk" value="18" delta="3 unaddressed" tone="danger" />
        <KpiTile label="Stalled" value="72" delta=">21d no improvement" tone="warn" />
        <KpiTile label="Healing" value="23" delta="≥10% area Δ" tone="success" />
        <KpiTile label="New (mo)" value="12" delta="referral mix 6/12" />
      </section>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-[1fr_400px]">
        <div className="card overflow-hidden">
          <div className="flex items-center justify-between gap-3 border-b border-hairline bg-surface-2 px-4 py-3 text-xs">
            <div className="flex flex-wrap gap-1.5">
              <Chip active>All ({PATIENTS.length})</Chip>
              <Chip>Active ({PATIENTS.filter((p) => p.status === "active").length})</Chip>
              <Chip>High-risk ({PATIENTS.filter((p) => p.status === "high-risk").length})</Chip>
              <Chip>Remission ({PATIENTS.filter((p) => p.status === "remission").length})</Chip>
              <Chip>Discharged ({PATIENTS.filter((p) => p.status === "discharged").length})</Chip>
            </div>
            <span className="text-ink-muted">Showing {PATIENTS.length} of 128</span>
          </div>
          <div className="overflow-x-auto">
            <table className="table-base">
              <thead>
                <tr>
                  <th>Patient</th>
                  <th>MRN</th>
                  <th>Primary diagnosis</th>
                  <th className="text-right">Wounds</th>
                  <th className="text-right">Healing</th>
                  <th>Status</th>
                  <th>Last seen</th>
                  <th>Clinician</th>
                </tr>
              </thead>
              <tbody>
                {PATIENTS.map((p) => (
                  <tr key={p.id} className="hover:bg-surface-2">
                    <td>
                      <div className="flex items-center gap-2">
                        <span className="grid h-7 w-7 place-items-center rounded-full bg-accent/15 text-[10px] font-bold text-accent">
                          {p.name.split(" ").map((s) => s[0]).slice(0, 2).join("")}
                        </span>
                        <Link href={`/patients/${p.id}`} className="font-medium text-ink hover:text-accent">
                          {p.name}
                        </Link>
                      </div>
                    </td>
                    <td className="font-mono text-xs">{p.mrn}</td>
                    <td className="max-w-[260px] truncate" title={p.primaryDx}>
                      {p.primaryDx}
                    </td>
                    <td className="text-right tabular-nums">{p.woundCount}</td>
                    <td className="text-right">
                      <HealingBar pct={p.healingPct} />
                    </td>
                    <td>
                      <StatusPill status={p.status} />
                    </td>
                    <td className="whitespace-nowrap text-ink-muted">{fmtDate(p.lastSeen)}</td>
                    <td className="text-ink-muted">{p.clinician}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <PatientDetail />
      </div>
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

function HealingBar({ pct }: { pct: number }) {
  const tone = pct >= 70 ? "success" : pct >= 35 ? "accent" : "warn";
  return (
    <div className="flex items-center justify-end gap-2">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-hairline">
        <span className="block h-full" style={{ width: `${pct}%`, background: `rgb(var(--${tone}))` }} />
      </div>
      <span className="font-mono text-[11px] text-ink-soft">{pct}%</span>
    </div>
  );
}

function StatusPill({ status }: { status: "active" | "remission" | "discharged" | "high-risk" }) {
  const cls = {
    active: "pill pill-accent",
    remission: "pill pill-success",
    discharged: "pill pill-neutral",
    "high-risk": "pill pill-danger",
  }[status];
  const label = { active: "Active", remission: "Remission", discharged: "Discharged", "high-risk": "High risk" }[status];
  return <span className={cls}>{label}</span>;
}

function PatientDetail() {
  const p = PATIENTS[0]!;
  const captures = ["Apr 29", "Apr 22", "Apr 15", "Apr 08", "Apr 01", "Mar 25"];
  const trend = [22.4, 21.1, 19.8, 19.0, 18.6, 18.7];
  return (
    <aside className="card flex flex-col gap-4 p-4">
      <header className="flex items-start gap-3">
        <span className="grid h-12 w-12 place-items-center rounded-full bg-accent/15 font-bold text-accent">
          PJ
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="truncate font-display text-lg font-semibold text-ink">{p.name}</h2>
          <p className="text-xs text-ink-muted">
            {p.age}{p.sex} · MRN {p.mrn} · Medicare A/B
          </p>
          <div className="mt-1 flex flex-wrap gap-1">
            <span className="pill pill-accent">Active</span>
            <span className="pill pill-warn">A1c 7.8</span>
            <span className="pill pill-neutral">Wagner 2</span>
          </div>
        </div>
      </header>

      <div className="rounded-md border border-hairline bg-surface-2 p-3">
        <p className="text-[11px] uppercase tracking-[0.14em] text-ink-muted">Primary diagnosis</p>
        <p className="mt-0.5 text-sm text-ink">{p.primaryDx}</p>
      </div>

      <div>
        <p className="mb-2 text-[11px] uppercase tracking-[0.14em] text-ink-muted">Recent 3D scans</p>
        <div className="grid grid-cols-3 gap-1.5">
          {captures.map((d, i) => (
            <ScanThumb key={d} date={d} index={i} />
          ))}
        </div>
      </div>

      <div className="rounded-md border border-hairline bg-surface-2 p-3">
        <div className="flex items-center justify-between">
          <p className="text-[11px] uppercase tracking-[0.14em] text-ink-muted">
            Surface area (cm²)
          </p>
          <span className="text-[11px] text-success">−16% over 6w</span>
        </div>
        <Sparkline
          data={trend.map((v, i) => ({ x: i, y: v, label: captures[trend.length - 1 - i] }))}
          height={80}
        />
      </div>

      <div className="grid grid-cols-3 gap-2">
        <Stat label="Visits" value="6" />
        <Stat label="Days in care" value="84" />
        <Stat label="Healing" value={`${p.healingPct}%`} tone="accent" />
      </div>

      <div>
        <p className="text-[11px] uppercase tracking-[0.14em] text-ink-muted">Care plan</p>
        <ul className="mt-1.5 space-y-1.5 text-xs">
          {[
            "Total contact cast — change weekly",
            "ActiGraft+ application q14d",
            "Vascular reassessment in 30 days",
            "A1c monitoring with PCP",
          ].map((s, i) => (
            <li key={i} className="flex gap-2 text-ink-soft">
              <span className="mt-0.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
              {s}
            </li>
          ))}
        </ul>
      </div>

      <div className="rounded-md border border-warn/40 bg-warn/5 p-3 text-xs">
        <p className="font-semibold text-warn">Documentation flags</p>
        <ul className="mt-1 space-y-0.5 text-ink-soft">
          <li>· Photo evidence missing on visit Apr 22</li>
          <li>· Q-code attestation pending for AO-291</li>
        </ul>
      </div>

      <div className="mt-auto flex gap-2">
        <Link href="/wounds" className="btn btn-primary flex-1 justify-center">
          Open 3D analysis
        </Link>
        <Link href="/notes" className="btn btn-secondary flex-1 justify-center">
          Draft note
        </Link>
      </div>
    </aside>
  );
}

function ScanThumb({ date, index }: { date: string; index: number }) {
  // Stylised wound thumbnail — the size and intensity recede with each capture
  // to imply healing progress.
  const r = 22 - index * 1.5;
  return (
    <div className="aspect-square rounded-md border border-hairline bg-[#0a1428] p-1">
      <svg viewBox="0 0 60 60" className="h-full w-full">
        <defs>
          <radialGradient id={`wf${index}`} cx="50%" cy="50%" r="55%">
            <stop offset="0%" stopColor="#7a1d1d" />
            <stop offset="55%" stopColor="#b34141" />
            <stop offset="85%" stopColor="#3a2a2a" />
            <stop offset="100%" stopColor="transparent" />
          </radialGradient>
        </defs>
        <circle cx="30" cy="30" r="28" fill="url(#wf0)" opacity="0.05" />
        <ellipse cx="30" cy="30" rx={r} ry={r * 0.7} fill={`url(#wf${index})`} />
      </svg>
      <p className="mt-0.5 text-center font-mono text-[9px] text-ink-muted">{date}</p>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "accent" }) {
  return (
    <div className="rounded border border-hairline bg-surface-2 p-2 text-center">
      <div className="text-[10px] uppercase tracking-[0.14em] text-ink-muted">{label}</div>
      <div className={`mt-0.5 font-display text-lg font-semibold ${tone === "accent" ? "text-accent" : "text-ink"}`}>
        {value}
      </div>
    </div>
  );
}
