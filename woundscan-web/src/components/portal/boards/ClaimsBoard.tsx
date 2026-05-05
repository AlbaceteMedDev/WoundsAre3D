"use client";

import { useMemo, useState } from "react";
import { CLAIMS, REIMBURSEMENT_TREND } from "@/lib/sample";
import { fmtDate, money } from "@/lib/format";
import { KpiTile } from "@/components/portal/KpiTile";
import { Donut } from "@/components/portal/Donut";
import { Sparkline } from "@/components/portal/Sparkline";

const FILTERS = ["All", "Paid", "Pending", "Denied", "Appeal"] as const;
type Filter = (typeof FILTERS)[number];

const PAYER_MIX = [
  { payer: "Medicare A/B", pct: 48, color: "rgb(var(--accent))" },
  { payer: "Aetna",        pct: 17, color: "rgb(var(--success))" },
  { payer: "BCBS",         pct: 14, color: "rgb(var(--warn))" },
  { payer: "United",       pct: 11, color: "rgb(135 140 160)" },
  { payer: "Cigna",        pct: 6,  color: "rgb(var(--danger))" },
  { payer: "Other",        pct: 4,  color: "rgb(180 180 200)" },
] as const;

const AGING = [
  { bucket: "0-30 d",  amount: 21_400 },
  { bucket: "31-60 d", amount: 9_840 },
  { bucket: "61-90 d", amount: 2_120 },
  { bucket: "91+ d",   amount: 760 },
];

const DENIAL_REASONS = [
  { code: "CO-50", reason: "Medical necessity",          count: 4 },
  { code: "CO-16", reason: "Missing/invalid info",       count: 2 },
  { code: "CO-97", reason: "Bundled service",            count: 2 },
  { code: "CO-22", reason: "Coordination of benefits",   count: 1 },
];

export function ClaimsBoard() {
  const [filter, setFilter] = useState<Filter>("All");
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string>(CLAIMS[0]?.id ?? "");

  const filtered = useMemo(() => {
    let rows = CLAIMS;
    if (filter !== "All") {
      const target = filter.toLowerCase();
      rows = rows.filter((c) => c.status === target);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      rows = rows.filter(
        (c) => c.id.toLowerCase().includes(q) || c.patient.toLowerCase().includes(q) || c.cpt.includes(q),
      );
    }
    return rows;
  }, [filter, search]);

  const selected = CLAIMS.find((c) => c.id === selectedId) ?? CLAIMS[0]!;

  return (
    <>
      <section className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <KpiTile label="Total reimbursement" value={money(237_890)} delta="+13% MoM" tone="accent" />
        <KpiTile label="Claims (mo)" value="142" delta="+18 vs Mar" tone="accent" />
        <KpiTile label="Pending" value="9" delta="3 over 30d" tone="warn" />
        <KpiTile label="Denied" value="3.9%" delta="−0.7pp" tone="success" />
        <KpiTile label="Avg days to pay" value="14.2" delta="−2.1 days" tone="success" />
        <KpiTile label="First-pass rate" value="89.6%" delta="+4.2pp" tone="success" />
      </section>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-[1fr_360px]">
        <div className="card overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-hairline bg-surface-2 px-4 py-3 text-xs">
            <div className="flex flex-wrap gap-1.5">
              {FILTERS.map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setFilter(f)}
                  className={`inline-flex items-center rounded-full px-2.5 py-1 font-medium transition ${
                    filter === f ? "bg-accent/15 text-accent" : "border border-hairline text-ink-soft hover:border-accent hover:text-accent"
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
            <div className="flex flex-1 items-center gap-2 md:flex-none">
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search claims, CPT, patient…"
                className="input w-full md:w-64"
              />
              <button className="btn btn-secondary">Export 837P</button>
            </div>
          </div>

          {/* Desktop */}
          <div className="hidden overflow-x-auto md:block">
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
                {filtered.map((c) => (
                  <tr
                    key={c.id}
                    className={`cursor-pointer transition ${c.id === selectedId ? "bg-accent/10" : "hover:bg-surface-2"}`}
                    onClick={() => setSelectedId(c.id)}
                  >
                    <td className="font-mono text-xs">{c.id}</td>
                    <td>{c.patient}</td>
                    <td className="font-mono text-xs">{c.cpt}</td>
                    <td className="whitespace-nowrap text-right text-ink-muted">{fmtDate(c.submitted)}</td>
                    <td className="text-right tabular-nums">{money(c.amount)}</td>
                    <td className="text-right tabular-nums">{c.paid !== null ? money(c.paid) : "—"}</td>
                    <td><ClaimPill status={c.status} /></td>
                    <td className="text-ink-muted">{c.payer}</td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr><td colSpan={8} className="p-8 text-center text-ink-muted">No matching claims</td></tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Mobile */}
          <ul className="divide-y divide-hairline md:hidden">
            {filtered.map((c) => (
              <li
                key={c.id}
                onClick={() => setSelectedId(c.id)}
                className={`cursor-pointer p-3 ${c.id === selectedId ? "bg-accent/10" : ""}`}
              >
                <div className="flex items-baseline justify-between">
                  <span className="font-mono text-xs text-ink-muted">{c.id}</span>
                  <ClaimPill status={c.status} />
                </div>
                <div className="mt-1 font-medium text-ink">{c.patient}</div>
                <div className="text-xs text-ink-muted">CPT {c.cpt} · {c.payer}</div>
                <div className="mt-1 flex items-baseline justify-between text-xs">
                  <span className="text-ink-muted">{fmtDate(c.submitted)}</span>
                  <span className="font-semibold text-ink">{money(c.amount)}</span>
                </div>
              </li>
            ))}
          </ul>

          <div className="grid grid-cols-1 gap-4 border-t border-hairline p-4 md:grid-cols-3">
            <div className="card p-3">
              <span className="eyebrow">Reimbursement trend</span>
              <h3 className="mt-1 text-sm font-medium text-ink">Allowed amount by month ($K)</h3>
              <Sparkline
                data={REIMBURSEMENT_TREND.map((p, i) => ({ x: i, y: p.paid / 1000, label: p.mo }))}
                height={120}
              />
            </div>

            <div className="card p-3">
              <span className="eyebrow">Reimbursement by payer</span>
              <div className="mt-2 flex items-center gap-3">
                <Donut
                  size={100}
                  segments={PAYER_MIX.map((p) => ({ value: p.pct, color: p.color }))}
                  centerLabel="$237K"
                  centerSub="MTD"
                />
                <ul className="space-y-1 text-[11px]">
                  {PAYER_MIX.slice(0, 5).map((p) => (
                    <li key={p.payer} className="flex items-center justify-between text-ink-soft">
                      <span className="flex items-center gap-2">
                        <span className="inline-block h-2 w-2 rounded-full" style={{ background: p.color }} />
                        {p.payer}
                      </span>
                      <span className="tabular-nums text-ink-muted">{p.pct}%</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="card p-3">
              <span className="eyebrow">Aging summary</span>
              <h3 className="mt-1 text-sm font-medium text-ink">Outstanding A/R</h3>
              <ul className="mt-2 space-y-1.5 text-xs">
                {AGING.map((a) => {
                  const max = AGING[0]!.amount;
                  const pct = (a.amount / max) * 100;
                  const tone = a.bucket === "91+ d" ? "danger" : a.bucket === "61-90 d" ? "warn" : "accent";
                  return (
                    <li key={a.bucket}>
                      <div className="flex justify-between">
                        <span className="text-ink-soft">{a.bucket}</span>
                        <span className="tabular-nums text-ink">{money(a.amount)}</span>
                      </div>
                      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-hairline">
                        <span className="block h-full" style={{ width: `${pct}%`, background: `rgb(var(--${tone}))` }} />
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>
        </div>

        <ClaimDetail claim={selected} />
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
    </>
  );
}

function ClaimPill({ status }: { status: "paid" | "pending" | "denied" | "appeal" }) {
  const map = { paid: "pill pill-success", pending: "pill pill-accent", denied: "pill pill-danger", appeal: "pill pill-warn" };
  return <span className={map[status]}>{status}</span>;
}

function ClaimDetail({ claim }: { claim: typeof CLAIMS[number] }) {
  const risk = claim.status === "denied" ? "high" : claim.status === "appeal" ? "elevated" : "low";
  const ringDeg = risk === "high" ? 90 : risk === "elevated" ? 200 : 340;
  const ringColor = risk === "high" ? "var(--danger)" : risk === "elevated" ? "var(--warn)" : "var(--success)";
  return (
    <aside className="card flex flex-col gap-3 p-4">
      <header className="flex items-start justify-between gap-2">
        <div>
          <span className="eyebrow">Claim detail</span>
          <h2 className="mt-1 font-display text-base font-semibold text-ink">{claim.id}</h2>
          <p className="text-xs text-ink-muted">{claim.patient} · {claim.payer}</p>
        </div>
        <span
          className={`pill ${risk === "high" ? "pill-danger" : risk === "elevated" ? "pill-warn" : "pill-success"}`}
        >
          {risk === "high" ? "High risk" : risk === "elevated" ? "Elevated" : "Low risk"}
        </span>
      </header>

      <div className="flex items-center gap-3">
        <div
          className="grid h-[88px] w-[88px] place-items-center rounded-full"
          style={{ background: `conic-gradient(rgb(${ringColor}) ${ringDeg}deg, rgb(var(--hairline)) 0)` }}
        >
          <div className="grid h-[68px] w-[68px] place-items-center rounded-full bg-surface">
            <span className="font-display text-xl font-bold text-ink">
              {Math.round((ringDeg / 360) * 100)}%
            </span>
          </div>
        </div>
        <div className="flex-1 text-xs">
          <p className="font-semibold text-ink">Medical-necessity confidence</p>
          <p className="mt-0.5 text-ink-muted">
            Computed from objective measurement, conservative-care duration, and LCD coverage rules.
          </p>
        </div>
      </div>

      <ul className="space-y-1 text-xs">
        <Row label="Service date" value={fmtDate(claim.submitted)} />
        <Row label="Submitted" value={fmtDate(claim.submitted)} />
        <Row label="Adjudicated" value={claim.adjudicated ? fmtDate(claim.adjudicated) : "—"} />
        <Row label="CPT" value={claim.cpt} mono />
        <Row label="Allowed" value={money(claim.amount)} />
        <Row label="Paid" value={claim.paid !== null ? money(claim.paid) : "—"} bold />
      </ul>

      <div className={`rounded-md border p-3 text-xs ${
        risk === "high" ? "border-danger/40 bg-danger/10 text-danger" :
        risk === "elevated" ? "border-warn/40 bg-warn/10 text-warn" :
        "border-success/40 bg-success/10 text-success"
      }`}>
        {risk === "high"
          ? "Denied. Add MN narrative + LCD citation, then resubmit as appeal."
          : risk === "elevated"
            ? "Appeal in progress. Auto-attached objective measurements + conservative care timeline."
            : "Paid in full within payer timeline. No action required."}
      </div>

      <div>
        <p className="text-[11px] uppercase tracking-[0.14em] text-ink-muted">Linked artifacts</p>
        <ul className="mt-1.5 space-y-1 text-xs">
          <li className="flex justify-between"><span>Progression note</span><a className="text-accent hover:text-accent-bright" href="#">view ↗</a></li>
          <li className="flex justify-between"><span>3D scan record</span><a className="text-accent hover:text-accent-bright" href="#">view ↗</a></li>
          <li className="flex justify-between"><span>UDI graft application</span><a className="text-accent hover:text-accent-bright" href="#">view ↗</a></li>
          <li className="flex justify-between"><span>Pre-submission audit log</span><a className="text-accent hover:text-accent-bright" href="#">view ↗</a></li>
        </ul>
      </div>

      <button className="btn btn-secondary mt-auto justify-center">
        {risk === "low" ? "Open in EHR" : "Start correction"}
      </button>
    </aside>
  );
}

function Row({ label, value, bold, mono }: { label: string; value: string; bold?: boolean; mono?: boolean }) {
  return (
    <li className={`flex justify-between ${bold ? "border-t border-hairline pt-1.5 font-semibold text-ink" : "text-ink-soft"}`}>
      <span>{label}</span>
      <span className={`tabular-nums ${mono ? "font-mono text-xs" : ""}`}>{value}</span>
    </li>
  );
}
