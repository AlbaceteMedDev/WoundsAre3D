"use client";

import { KpiTile } from "@/components/portal/KpiTile";
import { Donut } from "@/components/portal/Donut";
import { ACTIVITY } from "@/lib/sample";
import { ViewHeader, type TourNavigate } from "./shared";

/** Landing view — every tile and row navigates somewhere real. */
export function DashboardView({ go }: { go: TourNavigate }) {
  return (
    <div className="space-y-4">
      <ViewHeader
        title="Clinical Operating Dashboard"
        sub="Audit-ready by design · Tuesday, May 12, 2026 · everything below is clickable"
      />
      <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-4">
        <Tap onClick={() => go("routes")}>
          <KpiTile label="Today's patients" value="5" delta="3 home · 2 clinic → routes" tone="accent" />
        </Tap>
        <Tap onClick={() => go("patients")}>
          <KpiTile label="Active patients" value="128" delta="+12 this week → roster" tone="accent" />
        </Tap>
        <Tap onClick={() => go("patients")}>
          <KpiTile label="High-risk" value="5" delta="2 unaddressed → roster" tone="warn" />
        </Tap>
        <Tap onClick={() => go("claims")}>
          <KpiTile label="Compliance score" value="96%" delta="audit-ready → checklist" tone="success" />
        </Tap>
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        <button type="button" onClick={() => go("patients")} className="card p-4 text-left transition hover:border-accent/50">
          <span className="eyebrow">Healing progress</span>
          <div className="mt-3 flex items-center gap-3">
            <Donut
              size={96}
              segments={[
                { value: 38, color: "rgb(var(--success))" },
                { value: 33, color: "rgb(var(--accent))" },
                { value: 18, color: "rgb(var(--warn))" },
                { value: 11, color: "rgb(var(--danger))" },
              ]}
              centerLabel="71%"
              centerSub="positive"
            />
            <ul className="flex-1 space-y-1 text-[11px] text-ink-soft">
              <li>38% on track</li>
              <li>33% tracking</li>
              <li>18% stalled</li>
              <li>11% worsening</li>
            </ul>
          </div>
        </button>

        <button type="button" onClick={() => go("claims")} className="card p-4 text-left transition hover:border-accent/50">
          <span className="eyebrow">Documentation integrity</span>
          <ul className="mt-3 space-y-2 text-[11px]">
            {[
              ["HCPCS", 98],
              ["LCD/NCD", 95],
              ["Photo evidence", 93],
              ["48h signatures", 97],
            ].map(([label, pct]) => (
              <li key={label as string}>
                <div className="flex justify-between text-ink-soft">
                  <span>{label}</span>
                  <span className="tabular-nums text-ink">{pct}%</span>
                </div>
                <div className="mt-1 h-1 overflow-hidden rounded-full bg-hairline">
                  <span className="block h-full bg-success" style={{ width: `${pct}%` }} />
                </div>
              </li>
            ))}
          </ul>
        </button>

        <button type="button" onClick={() => go("claims")} className="card p-4 text-left transition hover:border-accent/50">
          <span className="eyebrow">April reimbursement</span>
          <p className="mt-2 font-display text-2xl font-semibold text-ink">$337,120</p>
          <p className="text-xs text-success">+13% vs March</p>
          <p className="mt-3 text-xs text-ink-muted">88.5% paid · 10.1% pending · 1.4% denied</p>
          <p className="mt-2 text-xs text-accent">View claims →</p>
        </button>
      </div>

      <div className="card p-4">
        <span className="eyebrow">Recent activity</span>
        <ul className="mt-2 divide-y divide-hairline">
          {ACTIVITY.slice(0, 5).map((a, i) => {
            const dest =
              a.what.includes("claim") || a.what.includes("Compliance")
                ? ("claims" as const)
                : a.what.includes("scan")
                  ? ("scan" as const)
                  : a.what.includes("order")
                    ? ("inventory" as const)
                    : ("notes" as const);
            return (
              <li key={i}>
                <button
                  type="button"
                  onClick={() => go(dest)}
                  className="flex w-full items-center gap-3 py-1.5 text-left text-xs transition hover:bg-surface-2"
                >
                  <span className="font-mono text-[10px] text-ink-muted">{a.at}</span>
                  <span className="font-medium text-ink">{a.who}</span>
                  <span className="text-ink-soft">{a.what}</span>
                  <span className="ml-auto hidden truncate text-ink-muted sm:block">{a.subject}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>

      {/* Quick actions — mirrors the real dashboard */}
      <div>
        <span className="eyebrow">Quick actions</span>
        <div className="mt-2 grid grid-cols-2 gap-2 lg:grid-cols-6">
          {(
            [
              ["◉", "Open 3D Scan", "scan"],
              ["✎", "Audit-Safe Note", "notes"],
              ["+", "Add Order", "inventory"],
              ["↳", "Optimize Route", "routes"],
              ["◇", "Assign Graft", "inventory"],
              ["≣", "Generate Report", "reports"],
            ] as const
          ).map(([icon, label, dest]) => (
            <button
              key={label}
              type="button"
              onClick={() => go(dest)}
              className="card flex items-center gap-2.5 p-2.5 text-left transition hover:border-accent/60 hover:bg-accent/5"
            >
              <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md bg-accent/15 font-display text-accent">
                {icon}
              </span>
              <span className="text-xs font-medium text-ink">{label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function Tap({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} className="text-left transition hover:opacity-90">
      {children}
    </button>
  );
}
