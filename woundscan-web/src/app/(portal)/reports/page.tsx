import { AppShell } from "@/components/portal/AppShell";
import { getSession } from "@/lib/auth";
import { KpiTile } from "@/components/portal/KpiTile";
import { Sparkline } from "@/components/portal/Sparkline";
import { Donut } from "@/components/portal/Donut";

const PATIENT_VOLUME = [
  { mo: "Sep", v: 84 },
  { mo: "Oct", v: 102 },
  { mo: "Nov", v: 118 },
  { mo: "Dec", v: 110 },
  { mo: "Jan", v: 134 },
  { mo: "Feb", v: 142 },
  { mo: "Mar", v: 158 },
  { mo: "Apr", v: 172 },
];

const HEALING_OUTCOMES = [
  { mo: "Sep", healed: 12, partial: 6, stalled: 3 },
  { mo: "Oct", healed: 16, partial: 7, stalled: 4 },
  { mo: "Nov", healed: 19, partial: 9, stalled: 4 },
  { mo: "Dec", healed: 17, partial: 8, stalled: 3 },
  { mo: "Jan", healed: 22, partial: 10, stalled: 4 },
  { mo: "Feb", healed: 25, partial: 9, stalled: 4 },
  { mo: "Mar", healed: 27, partial: 11, stalled: 5 },
  { mo: "Apr", healed: 31, partial: 12, stalled: 4 },
];

const AREA_REDUCTION = [
  { wk: "W1", r: 0 },
  { wk: "W2", r: 6 },
  { wk: "W3", r: 14 },
  { wk: "W4", r: 22 },
  { wk: "W5", r: 30 },
  { wk: "W6", r: 39 },
  { wk: "W7", r: 47 },
  { wk: "W8", r: 56 },
  { wk: "W9", r: 64 },
  { wk: "W10", r: 71 },
  { wk: "W11", r: 78 },
  { wk: "W12", r: 84 },
];

const CLINICIAN_PRODUCTIVITY = [
  { who: "Dr. Morgan",  visits: 38, scans: 47, notes: 41 },
  { who: "Dr. Romero",  visits: 32, scans: 35, notes: 33 },
  { who: "NP Adler",    visits: 29, scans: 31, notes: 30 },
  { who: "NP Vasquez",  visits: 24, scans: 23, notes: 22 },
];

const INSIGHTS = [
  { title: "Stalled DFU rate trending down", body: "Stalled-wound rate fell from 14.5% to 9.8% MoM after the 30-day reassessment policy went live." },
  { title: "Friday is your scan-volume peak", body: "Capture volume spikes 84% on Fridays. Consider load-shifting optional follow-ups to mid-week." },
  { title: "ActiGraft+ utilization up 22%", body: "Driven by Westside clinic (Dr. Romero). Expanding Q-code A2005 ASP+6% as the dominant graft pathway." },
];

export default async function ReportsPage() {
  const session = await getSession();
  return (
    <AppShell
      title="Reports & Analytics"
      subtitle="Healing outcomes · operational KPIs · payer mix"
      user={{ name: "Dr. Rachel Morgan", role: session?.role ?? "clinician" }}
    >
      <section className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <KpiTile label="Patients (12m)" value="2,487" delta="+18% YoY" tone="accent" />
        <KpiTile label="Wounds tracked" value="892" delta="+12% YoY" />
        <KpiTile label="Scans (12m)" value="2,113" delta="+24% YoY" tone="success" />
        <KpiTile label="Healing rate" value="68.3%" delta="+4.1pp YoY" tone="success" />
        <KpiTile label="Avg days to heal" value="49.2" delta="-3.8 days" tone="success" />
        <KpiTile label="Denial rate" value="1.6%" delta="-0.7pp" tone="success" />
      </section>

      <section className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="card p-4">
          <span className="eyebrow">Patient volume</span>
          <h2 className="mt-1 font-display text-base font-semibold text-ink">By month · trailing 8</h2>
          <div className="mt-3 flex h-[180px] items-end gap-1.5">
            {PATIENT_VOLUME.map((p) => (
              <div key={p.mo} className="flex flex-1 flex-col items-center gap-1">
                <div
                  className="w-full rounded-t bg-accent/70"
                  style={{ height: `${(p.v / 200) * 100}%` }}
                />
                <span className="text-[10px] text-ink-muted">{p.mo}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card p-4">
          <span className="eyebrow">Healing outcomes</span>
          <h2 className="mt-1 font-display text-base font-semibold text-ink">Stacked by month</h2>
          <div className="mt-3 flex h-[180px] items-end gap-1.5">
            {HEALING_OUTCOMES.map((p) => {
              const total = p.healed + p.partial + p.stalled;
              const max = 50;
              return (
                <div key={p.mo} className="flex flex-1 flex-col items-center gap-1">
                  <div className="flex w-full flex-col-reverse overflow-hidden rounded-t" style={{ height: `${(total / max) * 100}%` }}>
                    <span className="block bg-success/80" style={{ height: `${(p.healed / total) * 100}%` }} />
                    <span className="block bg-accent/80" style={{ height: `${(p.partial / total) * 100}%` }} />
                    <span className="block bg-warn/80" style={{ height: `${(p.stalled / total) * 100}%` }} />
                  </div>
                  <span className="text-[10px] text-ink-muted">{p.mo}</span>
                </div>
              );
            })}
          </div>
          <ul className="mt-3 flex justify-center gap-4 text-[11px]">
            <Legend color="rgb(var(--success))" label="Healed" />
            <Legend color="rgb(var(--accent))" label="Partial" />
            <Legend color="rgb(var(--warn))" label="Stalled" />
          </ul>
        </div>
      </section>

      <section className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="card p-4">
          <span className="eyebrow">Modality utilization</span>
          <h2 className="mt-1 font-display text-base font-semibold text-ink">By treatment</h2>
          <div className="mt-3 flex items-center gap-4">
            <Donut
              size={120}
              segments={[
                { value: 36, color: "rgb(var(--accent))" },
                { value: 24, color: "rgb(var(--success))" },
                { value: 18, color: "rgb(var(--warn))" },
                { value: 12, color: "rgb(135 140 160)" },
                { value: 10, color: "rgb(var(--danger))" },
              ]}
              centerLabel="2,487"
              centerSub="treatments"
            />
            <ul className="space-y-1 text-[11px]">
              <Legend color="rgb(var(--accent))" label="ActiGraft+" pct={36} />
              <Legend color="rgb(var(--success))" label="Collagen" pct={24} />
              <Legend color="rgb(var(--warn))" label="UltraMist" pct={18} />
              <Legend color="rgb(135 140 160)" label="NPWT" pct={12} />
              <Legend color="rgb(var(--danger))" label="Exosome" pct={10} />
            </ul>
          </div>
        </div>

        <div className="card p-4">
          <span className="eyebrow">Clinician productivity</span>
          <h2 className="mt-1 font-display text-base font-semibold text-ink">This month</h2>
          <table className="table-base mt-2">
            <thead>
              <tr>
                <th>Clinician</th>
                <th className="text-right">Visits</th>
                <th className="text-right">Scans</th>
                <th className="text-right">Notes</th>
              </tr>
            </thead>
            <tbody>
              {CLINICIAN_PRODUCTIVITY.map((c) => (
                <tr key={c.who}>
                  <td>{c.who}</td>
                  <td className="text-right tabular-nums">{c.visits}</td>
                  <td className="text-right tabular-nums">{c.scans}</td>
                  <td className="text-right tabular-nums">{c.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card p-4">
          <span className="eyebrow">Area reduction trend</span>
          <h2 className="mt-1 font-display text-base font-semibold text-ink">Cohort · 12 weeks</h2>
          <Sparkline
            data={AREA_REDUCTION.map((p, i) => ({ x: i, y: p.r, label: p.wk }))}
            height={180}
          />
          <p className="text-[11px] text-ink-muted">% area reduction from week 0</p>
        </div>
      </section>

      <section className="mt-6 card p-4">
        <span className="eyebrow">Key insights</span>
        <h2 className="mt-1 font-display text-base font-semibold text-ink">Auto-surfaced this period</h2>
        <ul className="mt-3 grid gap-2 md:grid-cols-3">
          {INSIGHTS.map((p, i) => (
            <li key={i} className="rounded-md border border-hairline bg-surface p-3">
              <div className="font-medium text-ink">{p.title}</div>
              <p className="mt-1 text-xs text-ink-muted">{p.body}</p>
            </li>
          ))}
        </ul>
      </section>
    </AppShell>
  );
}

function Legend({ color, label, pct }: { color: string; label: string; pct?: number }) {
  return (
    <li className="flex items-center justify-between text-ink-soft">
      <span className="flex items-center gap-2">
        <span className="inline-block h-2 w-2 rounded-full" style={{ background: color }} />
        {label}
      </span>
      {pct !== undefined && <span className="tabular-nums text-ink-muted">{pct}%</span>}
    </li>
  );
}
