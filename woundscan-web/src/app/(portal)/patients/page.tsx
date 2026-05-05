import Link from "next/link";
import { AppShell } from "@/components/portal/AppShell";
import { getSession } from "@/lib/auth";
import { PATIENTS } from "@/lib/sample";
import { fmtDate } from "@/lib/format";

export default async function PatientRosterPage() {
  const session = await getSession();
  return (
    <AppShell
      title="Patient Roster"
      subtitle={`${PATIENTS.length} patients · sorted by last seen`}
      user={{ name: "Dr. Rachel Morgan", role: session?.role ?? "clinician" }}
    >
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_360px]">
        <div className="card overflow-hidden">
          <div className="flex items-center justify-between gap-3 border-b border-hairline bg-surface-2 px-4 py-3 text-xs">
            <div className="flex gap-1.5">
              <Chip active>All patients ({PATIENTS.length})</Chip>
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
                          {p.name
                            .split(" ")
                            .map((s) => s[0])
                            .slice(0, 2)
                            .join("")}
                        </span>
                        <Link href={`/patients/${p.id}`} className="font-medium text-ink hover:text-accent">
                          {p.name}
                        </Link>
                      </div>
                    </td>
                    <td className="font-mono text-xs">{p.mrn}</td>
                    <td className="max-w-[260px] truncate" title={p.primaryDx}>{p.primaryDx}</td>
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
  const fill = `rgb(var(--${tone}))`;
  return (
    <div className="flex items-center justify-end gap-2">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-hairline">
        <span className="block h-full" style={{ width: `${pct}%`, background: fill }} />
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
  return (
    <aside className="card flex flex-col gap-4 p-4">
      <header className="flex items-center gap-3">
        <span className="grid h-12 w-12 place-items-center rounded-full bg-accent/15 font-bold text-accent">
          PJ
        </span>
        <div className="min-w-0">
          <h2 className="truncate font-display text-lg font-semibold text-ink">{p.name}</h2>
          <p className="text-xs text-ink-muted">
            {p.age}{p.sex} · MRN {p.mrn}
          </p>
        </div>
      </header>

      <div className="rounded-md border border-hairline bg-surface-2 p-3">
        <p className="text-[11px] uppercase tracking-[0.14em] text-ink-muted">Primary diagnosis</p>
        <p className="mt-0.5 text-sm text-ink">{p.primaryDx}</p>
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

      <div>
        <p className="text-[11px] uppercase tracking-[0.14em] text-ink-muted">Recent activity</p>
        <ul className="mt-1.5 space-y-1 text-xs">
          <li className="text-ink-soft">Apr 29 · 3D scan captured (grade B)</li>
          <li className="text-ink-soft">Apr 22 · Note signed by Dr. Morgan</li>
          <li className="text-ink-soft">Apr 22 · ActiGraft+ 4×4 applied</li>
          <li className="text-ink-soft">Apr 15 · 3D scan captured (grade A)</li>
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
