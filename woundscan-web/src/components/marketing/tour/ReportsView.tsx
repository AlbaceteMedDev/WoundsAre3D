"use client";

import { useState } from "react";
import { KpiTile } from "@/components/portal/KpiTile";
import { Sparkline } from "@/components/portal/Sparkline";
import { Chip, ViewHeader } from "./shared";

const PATIENT_VOLUME = [
  { mo: "Sep", v: 84 }, { mo: "Oct", v: 102 }, { mo: "Nov", v: 118 }, { mo: "Dec", v: 110 },
  { mo: "Jan", v: 134 }, { mo: "Feb", v: 142 }, { mo: "Mar", v: 158 }, { mo: "Apr", v: 172 },
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

const AREA_REDUCTION = Array.from({ length: 12 }, (_, i) => ({
  wk: `W${i + 1}`,
  r: [0, 6, 14, 22, 30, 39, 47, 56, 64, 71, 78, 84][i]!,
}));

const PRODUCTIVITY = [
  { who: "Dr. Morgan", visits: 38, scans: 47, notes: 41 },
  { who: "Dr. Romero", visits: 32, scans: 35, notes: 33 },
  { who: "NP Adler", visits: 29, scans: 31, notes: 30 },
  { who: "NP Vasquez", visits: 24, scans: 23, notes: 22 },
];

const TABS = ["Outcomes", "Operations", "Insights"] as const;

/** Analytics with switchable report tabs and a simulated export flow. */
export function ReportsView() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Outcomes");
  const [exported, setExported] = useState(false);

  return (
    <div className="space-y-4">
      <ViewHeader
        title="Reports & Analytics"
        sub="Healing outcomes · operational KPIs · payer mix"
        right={
          <button
            type="button"
            onClick={() => {
              setExported(true);
              setTimeout(() => setExported(false), 2600);
            }}
            className="btn btn-secondary text-xs"
          >
            {exported ? "✓ Queued — PDF + CSV + FHIR" : "Export report"}
          </button>
        }
      />

      <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-4">
        <KpiTile label="Patients (12m)" value="2,487" delta="+18% YoY" tone="accent" />
        <KpiTile label="Healing rate" value="68.3%" delta="+4.1pp YoY" tone="success" />
        <KpiTile label="Avg days to heal" value="49.2" delta="−3.8 days" tone="success" />
        <KpiTile label="Denial rate" value="1.6%" delta="−0.7pp" tone="success" />
      </div>

      <div className="flex flex-wrap gap-1.5">
        {TABS.map((t) => (
          <Chip key={t} active={tab === t} onClick={() => setTab(t)}>
            {t}
          </Chip>
        ))}
      </div>

      {tab === "Outcomes" && (
        <div className="grid gap-3 lg:grid-cols-2">
          <div className="card p-4">
            <span className="eyebrow">Healing outcomes · stacked by month</span>
            <div className="mt-3 flex h-[150px] items-end gap-1.5">
              {HEALING_OUTCOMES.map((p) => {
                const total = p.healed + p.partial + p.stalled;
                return (
                  <div key={p.mo} className="flex flex-1 flex-col items-center gap-1">
                    <div className="flex w-full flex-col-reverse overflow-hidden rounded-t" style={{ height: `${(total / 50) * 100}%` }}>
                      <span className="block bg-success/80" style={{ height: `${(p.healed / total) * 100}%` }} title={`${p.healed} healed`} />
                      <span className="block bg-accent/80" style={{ height: `${(p.partial / total) * 100}%` }} title={`${p.partial} partial`} />
                      <span className="block bg-warn/80" style={{ height: `${(p.stalled / total) * 100}%` }} title={`${p.stalled} stalled`} />
                    </div>
                    <span className="text-[10px] text-ink-muted">{p.mo}</span>
                  </div>
                );
              })}
            </div>
            <p className="mt-2 text-center text-[10px] text-ink-muted">
              green healed · blue partial · amber stalled
            </p>
          </div>
          <div className="card p-4">
            <span className="eyebrow">Mean area reduction · % from baseline</span>
            <Sparkline data={AREA_REDUCTION.map((p, i) => ({ x: i, label: i % 2 ? undefined : p.wk, y: p.r }))} height={150} />
            <p className="mt-1 text-center text-[10px] text-ink-muted">
              84% mean reduction by week 12 across tracked wounds
            </p>
          </div>
        </div>
      )}

      {tab === "Operations" && (
        <div className="grid gap-3 lg:grid-cols-2">
          <div className="card p-4">
            <span className="eyebrow">Patient volume · trailing 8 months</span>
            <div className="mt-3 flex h-[150px] items-end gap-1.5">
              {PATIENT_VOLUME.map((p) => (
                <div key={p.mo} className="flex flex-1 flex-col items-center gap-1">
                  <div className="w-full rounded-t bg-accent/70 transition hover:bg-accent" style={{ height: `${(p.v / 200) * 100}%` }} title={`${p.v} patients`} />
                  <span className="text-[10px] text-ink-muted">{p.mo}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="card overflow-x-auto !p-0">
            <table className="table-base">
              <thead>
                <tr>
                  <th>Clinician</th>
                  <th className="text-right">Visits</th>
                  <th className="text-right">Scans</th>
                  <th className="text-right">Notes</th>
                  <th className="text-right">Scans / visit</th>
                </tr>
              </thead>
              <tbody>
                {PRODUCTIVITY.map((r) => (
                  <tr key={r.who} className="hover:bg-surface-2">
                    <td className="font-medium text-ink">{r.who}</td>
                    <td className="text-right tabular-nums">{r.visits}</td>
                    <td className="text-right tabular-nums">{r.scans}</td>
                    <td className="text-right tabular-nums">{r.notes}</td>
                    <td className="text-right tabular-nums text-accent">{(r.scans / r.visits).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "Insights" && (
        <div className="grid gap-3 lg:grid-cols-3">
          {[
            { title: "Stalled DFU rate trending down", body: "Stalled-wound rate fell from 14.5% to 9.8% MoM after the 30-day reassessment policy went live." },
            { title: "Friday is your scan-volume peak", body: "Capture volume spikes 84% on Fridays. Consider load-shifting optional follow-ups to mid-week." },
            { title: "ActiGraft+ utilization up 22%", body: "Driven by Westside clinic (Dr. Romero). Q-code A2005 ASP+6% is now the dominant graft pathway." },
          ].map((c) => (
            <article key={c.title} className="card p-4">
              <h4 className="font-display text-sm font-semibold text-ink">{c.title}</h4>
              <p className="mt-1.5 text-xs leading-relaxed text-ink-soft">{c.body}</p>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
