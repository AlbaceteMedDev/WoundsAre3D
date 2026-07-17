"use client";

import Link from "next/link";
import { useState } from "react";
import { Reveal } from "./Reveal";
import { KpiTile } from "@/components/portal/KpiTile";
import { Donut } from "@/components/portal/Donut";
import { Sparkline } from "@/components/portal/Sparkline";
import { PATIENTS, CLAIMS, ACTIVITY } from "@/lib/sample";

type View = "dashboard" | "patients" | "wound" | "inventory" | "claims";

const NAV: Array<{ key: View; label: string; icon: string }> = [
  { key: "dashboard", label: "Dashboard", icon: "▦" },
  { key: "patients", label: "Patients", icon: "☺" },
  { key: "wound", label: "Wound record", icon: "◉" },
  { key: "inventory", label: "Inventory", icon: "◇" },
  { key: "claims", label: "Claims & compliance", icon: "✓" },
];

const LOCKED = ["Notes", "Reports", "Routes", "Admin"];

/**
 * Interactive portal tour: a simulated portal window rendering condensed,
 * faithful replicas of the real portal views (same components, same
 * design system, synthetic data) so providers can explore the EHR-like
 * layer — patient tracking, documentation compliance, inventory/UDI
 * traceability, claims — without an account.
 */
export function PortalTourSection() {
  const [view, setView] = useState<View>("dashboard");

  return (
    <section id="portal" className="relative scroll-mt-20 py-20 md:py-28">
      <div className="mk-section">
        <Reveal>
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <span className="eyebrow">Inside the portal — click around</span>
              <h2 className="mk-h2 mt-3">
                The whole wound service line. <span className="text-gradient">One login.</span>
              </h2>
              <p className="mk-lead">
                Measurement is where it starts, not where it ends. The portal wraps EHR-grade
                patient tracking, audit-ready documentation, UDI-traceable inventory, and claims
                visibility around every 3D capture — explore a working replica below with
                synthetic data.
              </p>
            </div>
            <span className="mk-chip">
              <span className="mk-live-dot inline-block h-1.5 w-1.5 rounded-full bg-success" />
              simulated · no PHI
            </span>
          </div>
        </Reveal>

        <Reveal delay={120}>
          <div className="card mt-10 overflow-hidden !rounded-xl shadow-elevated">
            {/* Window chrome */}
            <div className="flex items-center justify-between border-b border-hairline bg-surface-2/60 px-4 py-2.5">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-danger/50" />
                <span className="h-2.5 w-2.5 rounded-full bg-warn/50" />
                <span className="h-2.5 w-2.5 rounded-full bg-success/50" />
              </div>
              <p className="hidden font-mono text-[11px] text-ink-muted sm:block">
                portal.stratametricai.com · Dr. Rachel Morgan · clinician
              </p>
              <span className="pill pill-accent">demo mode</span>
            </div>

            <div className="grid md:grid-cols-[200px_1fr]">
              {/* Sidebar */}
              <aside className="border-b border-hairline bg-surface-2/40 md:border-b-0 md:border-r">
                <nav className="flex gap-1 overflow-x-auto p-2 md:flex-col md:overflow-visible md:p-3" aria-label="Portal views">
                  {NAV.map((n) => (
                    <button
                      key={n.key}
                      type="button"
                      onClick={() => setView(n.key)}
                      aria-pressed={view === n.key}
                      className={`flex shrink-0 items-center gap-2.5 rounded-md px-3 py-2 text-left text-sm font-medium transition ${
                        view === n.key
                          ? "bg-accent/10 text-accent"
                          : "text-ink-soft hover:bg-surface hover:text-ink"
                      }`}
                    >
                      <span aria-hidden className="w-4 text-center">{n.icon}</span>
                      {n.label}
                    </button>
                  ))}
                  <div className="my-1 hidden border-t border-hairline md:block" />
                  {LOCKED.map((l) => (
                    <span
                      key={l}
                      className="hidden items-center gap-2.5 rounded-md px-3 py-2 text-sm text-ink-muted/60 md:flex"
                      title="Available in the full portal"
                    >
                      <span aria-hidden className="w-4 text-center">🔒</span>
                      {l}
                    </span>
                  ))}
                </nav>
              </aside>

              {/* Active view */}
              <div className="max-h-[600px] overflow-y-auto bg-bg/40 p-4 md:p-5">
                {view === "dashboard" && <DashboardView onOpenClaims={() => setView("claims")} />}
                {view === "patients" && <PatientsView onOpenChart={() => setView("wound")} />}
                {view === "wound" && <WoundRecordView />}
                {view === "inventory" && <InventoryView />}
                {view === "claims" && <ClaimsView />}
              </div>
            </div>
          </div>
        </Reveal>

        <Reveal delay={200}>
          <div className="mt-8 grid gap-5 md:grid-cols-3">
            {[
              {
                t: "Documentation compliance",
                d: "Pre-audit checklists on every open case — HCPCS verification, LCD/NCD alignment, photo + 3D evidence, 48-hour signatures, medical-necessity narratives — scored continuously, not discovered at audit time.",
              },
              {
                t: "Patient & wound tracking",
                d: "Every patient, every wound, every visit: healing trajectories against weekly targets, stalled-wound flags, high-risk rosters, and a full measurement history behind each chart.",
              },
              {
                t: "Inventory & UDI traceability",
                d: "Serial, lot, and UDI recorded at the point of care. Graft units traced from manufacturer to application to claim — with expiration alerts and waste tracking built in.",
              },
            ].map((c) => (
              <article key={c.t} className="mk-card h-full">
                <h3 className="font-display text-base font-semibold text-ink">{c.t}</h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-soft">{c.d}</p>
              </article>
            ))}
          </div>
        </Reveal>

        <Reveal delay={260}>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link href="/login" className="btn btn-primary px-5 py-2.5">
              Sign in to the full portal
              <span aria-hidden>→</span>
            </Link>
            <a
              href="mailto:gabe@albacetemeddev.com?subject=StrataMetric%20AI%20portal%20walkthrough"
              className="btn btn-secondary px-5 py-2.5"
            >
              Book a guided walkthrough
            </a>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

/* ─────────────────────────── Dashboard ─────────────────────────── */

function DashboardView({ onOpenClaims }: { onOpenClaims: () => void }) {
  return (
    <div className="space-y-4">
      <ViewHeader
        title="Clinical Operating Dashboard"
        sub="Audit-ready by design · Tuesday, May 12, 2026"
      />
      <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-4">
        <KpiTile label="Today's patients" value="5" delta="3 home · 2 clinic" tone="accent" />
        <KpiTile label="Active patients" value="128" delta="+12 this week" tone="accent" />
        <KpiTile label="High-risk" value="5" delta="2 unaddressed" tone="warn" />
        <KpiTile label="Compliance score" value="96%" delta="audit-ready" tone="success" />
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        <div className="card p-4">
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
        </div>

        <div className="card p-4">
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
        </div>

        <button type="button" onClick={onOpenClaims} className="card p-4 text-left transition hover:border-accent/50">
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
          {ACTIVITY.slice(0, 5).map((a, i) => (
            <li key={i} className="flex items-center gap-3 py-1.5 text-xs">
              <span className="font-mono text-[10px] text-ink-muted">{a.at}</span>
              <span className="font-medium text-ink">{a.who}</span>
              <span className="text-ink-soft">{a.what}</span>
              <span className="ml-auto hidden truncate text-ink-muted sm:block">{a.subject}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/* ─────────────────────────── Patients ─────────────────────────── */

function PatientsView({ onOpenChart }: { onOpenChart: () => void }) {
  return (
    <div className="space-y-4">
      <ViewHeader title="Patients" sub="128 active · sorted by last seen" />
      <div className="card overflow-x-auto !p-0">
        <table className="table-base">
          <thead>
            <tr>
              <th>Patient</th>
              <th>Primary dx</th>
              <th>Status</th>
              <th>Healing</th>
              <th>Last seen</th>
            </tr>
          </thead>
          <tbody>
            {PATIENTS.slice(0, 8).map((p) => (
              <tr
                key={p.id}
                onClick={onOpenChart}
                className="cursor-pointer hover:bg-surface-2"
                title="Open wound record"
              >
                <td>
                  <div className="font-medium text-ink">{p.name}</div>
                  <div className="font-mono text-[10px] text-ink-muted">{p.mrn}</div>
                </td>
                <td className="max-w-[180px] truncate text-ink-soft">{p.primaryDx}</td>
                <td>
                  <span
                    className={`pill ${
                      p.status === "high-risk"
                        ? "pill-danger"
                        : p.status === "remission"
                          ? "pill-success"
                          : p.status === "discharged"
                            ? "pill-neutral"
                            : "pill-accent"
                    }`}
                  >
                    {p.status}
                  </span>
                </td>
                <td className="min-w-[110px]">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-hairline">
                      <span
                        className={`block h-full ${p.healingPct >= 60 ? "bg-success" : p.healingPct >= 30 ? "bg-accent" : "bg-warn"}`}
                        style={{ width: `${p.healingPct}%` }}
                      />
                    </div>
                    <span className="tabular-nums text-[11px] text-ink-muted">{p.healingPct}%</span>
                  </div>
                </td>
                <td className="whitespace-nowrap text-ink-muted">{p.lastSeen}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-center text-[11px] text-ink-muted">
        Click any row to open the wound record — this is live, try it.
      </p>
    </div>
  );
}

/* ─────────────────────────── Wound record ─────────────────────────── */

const VISITS = [
  { visit: "V6", date: "2026-04-29", area: 11.2, depth: 11.8, grade: "A" },
  { visit: "V5", date: "2026-04-22", area: 12.4, depth: 12.6, grade: "A" },
  { visit: "V4", date: "2026-04-15", area: 14.1, depth: 13.1, grade: "B" },
  { visit: "V3", date: "2026-04-08", area: 15.9, depth: 14.0, grade: "A" },
  { visit: "V2", date: "2026-04-01", area: 17.2, depth: 15.2, grade: "B" },
  { visit: "V1", date: "2026-03-25", area: 18.5, depth: 15.8, grade: "A" },
];

function WoundRecordView() {
  return (
    <div className="space-y-4">
      <ViewHeader
        title="Patricia Johnson · MRN-002847"
        sub="Diabetic foot ulcer, right plantar · wound 1 of 1 · Dr. Morgan"
      />

      <div className="grid gap-3 lg:grid-cols-[240px_1fr]">
        {/* Capture panel — the wound imaging side */}
        <div className="card p-3">
          <span className="eyebrow">Latest capture · V6</span>
          <div
            className="mt-2 overflow-hidden rounded-md"
            style={{ background: "radial-gradient(ellipse at 50% 42%, #0a1428 0%, #03060d 78%)" }}
          >
            <svg viewBox="0 0 220 170" className="w-full" role="img" aria-label="Stylized 3D wound capture with measurement overlay">
              <ellipse cx="110" cy="84" rx="72" ry="52" fill="#12233d" />
              <ellipse cx="110" cy="84" rx="52" ry="36" fill="#1d3a5f" />
              <ellipse cx="110" cy="84" rx="34" ry="23" fill="#2c5d8f" />
              <ellipse cx="110" cy="84" rx="18" ry="12" fill="#3f83bd" />
              <ellipse cx="110" cy="84" rx="72" ry="52" fill="none" stroke="#22d3ee" strokeWidth="1" strokeDasharray="4 4" opacity="0.7" />
              <line x1="38" y1="150" x2="182" y2="150" stroke="#22d3ee" strokeWidth="1" />
              <text x="92" y="146" fontSize="8" fontFamily="monospace" fill="#7dd3fc">L 42.0 mm</text>
              <circle cx="110" cy="84" r="4" fill="none" stroke="#fbbf24" strokeWidth="1" />
              <text x="118" y="80" fontSize="8" fontFamily="monospace" fill="#fbbf24">D 11.8</text>
            </svg>
          </div>
          <ul className="mt-2 grid grid-cols-2 gap-1.5 text-center text-[10px]">
            <MiniMetric k="Bed area" v="11.2 cm²" />
            <MiniMetric k="Max depth" v="11.8 mm" />
            <MiniMetric k="Peri-wound" v="18.4 cm²" />
            <MiniMetric k="Quality" v="Grade A" />
          </ul>
        </div>

        {/* Trajectory + history */}
        <div className="space-y-3">
          <div className="card p-4">
            <div className="flex items-baseline justify-between">
              <span className="eyebrow">Healing trajectory</span>
              <span className="text-[11px] text-success">−39.5% area over 5 weeks</span>
            </div>
            <Sparkline
              data={[...VISITS].reverse().map((v, i) => ({ x: i, label: v.visit, y: v.area }))}
              height={120}
            />
          </div>
          <div className="card overflow-x-auto !p-0">
            <table className="table-base">
              <thead>
                <tr>
                  <th>Visit</th>
                  <th>Date</th>
                  <th className="text-right">Bed area</th>
                  <th className="text-right">Max depth</th>
                  <th>Quality</th>
                </tr>
              </thead>
              <tbody>
                {VISITS.slice(0, 4).map((v) => (
                  <tr key={v.visit} className="hover:bg-surface-2">
                    <td className="font-mono text-xs">{v.visit}</td>
                    <td className="whitespace-nowrap text-ink-muted">{v.date}</td>
                    <td className="text-right tabular-nums">{v.area.toFixed(1)} cm²</td>
                    <td className="text-right tabular-nums">{v.depth.toFixed(1)} mm</td>
                    <td><span className={`pill ${v.grade === "A" ? "pill-success" : "pill-accent"}`}>{v.grade}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Documentation */}
      <div className="card p-4">
        <div className="flex items-center justify-between">
          <span className="eyebrow">Progression note · V6</span>
          <span className="pill pill-success">signed · Dr. Morgan · 08:42</span>
        </div>
        <p className="mt-2 text-xs leading-relaxed text-ink-soft">
          Wound bed area 11.2 cm² (−9.7% vs V5), max depth 11.8 mm from fitted reference plane.
          Peri-wound 18.4 cm². Measurements instrument-derived (3D LiDAR capture, quality A);
          methodology and algorithm versions attached to this note.
        </p>
        <p className="mt-2 font-mono text-[10px] text-ink-muted">
          provenance sha256:6b1f…9c2e · algo v1.0.0 · audit chain #4,182 ✓
        </p>
      </div>
    </div>
  );
}

/* ─────────────────────────── Inventory ─────────────────────────── */

const LEDGER = [
  { product: "ActiGraft+ 4×4", serial: "AG-291847", lot: "L-2604-A", udi: "(01)00875498003420", exp: "2026-08-22", status: "applied", patient: "P. Johnson" },
  { product: "ActiGraft+ 5×5", serial: "AG-291902", lot: "L-2604-A", udi: "(01)00875498003437", exp: "2026-08-22", status: "in-stock" },
  { product: "Collagen matrix 4×4", serial: "CM-100823", lot: "L-2603-C", udi: "(01)00875498005432", exp: "2027-03-30", status: "applied", patient: "R. Williams" },
  { product: "Adhesion barrier 5×5", serial: "AB-552031", lot: "L-2602-X", udi: "(01)00875498005111", exp: "2026-05-12", status: "expiring" },
  { product: "Exosome serum 0.5ml", serial: "EX-008713", lot: "L-2604-E", udi: "(01)00875498009012", exp: "2026-05-30", status: "in-stock" },
] as const;

function InventoryView() {
  return (
    <div className="space-y-4">
      <ViewHeader title="Inventory & Graft Tracking" sub="Real-time stock, lot management, graft traceability" />
      <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-4">
        <KpiTile label="On-hand units" value="2,847" delta="+148 this week" tone="accent" />
        <KpiTile label="Expires <30d" value="23" delta="6 require swap" tone="warn" />
        <KpiTile label="Waste" value="2.3%" delta="−0.4pp MoM" tone="success" />
        <KpiTile label="UDI compliance" value="100%" delta="all units traced" tone="success" />
      </div>

      <div className="card overflow-x-auto !p-0">
        <table className="table-base">
          <thead>
            <tr>
              <th>Product</th>
              <th>Serial / Lot</th>
              <th>UDI</th>
              <th>Expiration</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {LEDGER.map((r) => (
              <tr key={r.serial} className="hover:bg-surface-2">
                <td className="font-medium text-ink">{r.product}</td>
                <td>
                  <div className="font-mono text-xs">{r.serial}</div>
                  <div className="font-mono text-[10px] text-ink-muted">{r.lot}</div>
                </td>
                <td className="font-mono text-[11px]">{r.udi}</td>
                <td className="whitespace-nowrap text-ink-muted">{r.exp}</td>
                <td>
                  {r.status === "applied" ? (
                    <span className="pill pill-accent">applied · {"patient" in r ? r.patient : ""}</span>
                  ) : r.status === "expiring" ? (
                    <span className="pill pill-warn">expires soon</span>
                  ) : (
                    <span className="pill pill-success">in stock</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card p-4">
        <span className="eyebrow">Active graft trace · AG-291847</span>
        <ol className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-ink-soft">
          {["Manufactured 04-08", "Received Midtown 04-12", "Assigned P. Johnson 04-28", "Applied 14.7 cm² 04-29", "Claim CLM-00517 04-30"].map((s, i, arr) => (
            <li key={s} className="flex items-center gap-2">
              <span className="rounded border border-hairline bg-surface px-2 py-1">{s}</span>
              {i < arr.length - 1 && <span aria-hidden className="text-accent">→</span>}
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

/* ─────────────────────────── Claims & compliance ─────────────────────────── */

function ClaimsView() {
  return (
    <div className="space-y-4">
      <ViewHeader title="Claims & Compliance" sub="Reimbursement visibility with audit readiness built in" />
      <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-4">
        <KpiTile label="Compliance score" value="96%" delta="audit-ready" tone="success" />
        <KpiTile label="April paid" value="$298,400" delta="88.5% of billed" tone="accent" />
        <KpiTile label="Pending" value="$34,120" delta="10.1%" />
        <KpiTile label="Avg days to pay" value="14.2" delta="−1.8d vs Q1" tone="success" />
      </div>

      <div className="card overflow-x-auto !p-0">
        <table className="table-base">
          <thead>
            <tr>
              <th>Claim</th>
              <th>Patient</th>
              <th>CPT</th>
              <th>Payer</th>
              <th className="text-right">Amount</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {CLAIMS.slice(0, 6).map((c) => (
              <tr key={c.id} className="hover:bg-surface-2">
                <td className="font-mono text-[11px]">{c.id.replace("CLM-2026-", "…")}</td>
                <td className="whitespace-nowrap text-ink-soft">{c.patient}</td>
                <td className="font-mono text-xs">{c.cpt}</td>
                <td className="text-ink-muted">{c.payer}</td>
                <td className="text-right tabular-nums">${c.amount.toFixed(2)}</td>
                <td>
                  <span
                    className={`pill ${
                      c.status === "paid"
                        ? "pill-success"
                        : c.status === "denied"
                          ? "pill-danger"
                          : c.status === "appeal"
                            ? "pill-warn"
                            : "pill-accent"
                    }`}
                  >
                    {c.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card p-4">
        <span className="eyebrow">Pre-audit checklist · all open cases</span>
        <ul className="mt-2 grid gap-1.5 text-xs sm:grid-cols-2">
          {[
            ["HCPCS verification per product / payer", "pass"],
            ["LCD/NCD coverage alignment", "pass"],
            ["Photo + 3D evidence attached", "pass"],
            ["Notes signed within 48h", "warn"],
            ["UDI / serial / lot recorded", "pass"],
            ["Medical necessity narrative present", "warn"],
          ].map(([label, state]) => (
            <li key={label} className="flex items-center justify-between rounded-md border border-hairline bg-surface px-3 py-1.5">
              <span className="text-ink-soft">{label}</span>
              <span className={`pill ${state === "pass" ? "pill-success" : "pill-warn"}`}>
                {state === "pass" ? "PASS" : "REVIEW"}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/* ─────────────────────────── Shared bits ─────────────────────────── */

function ViewHeader({ title, sub }: { title: string; sub: string }) {
  return (
    <header>
      <h3 className="font-display text-lg font-semibold text-ink">{title}</h3>
      <p className="text-xs text-ink-muted">{sub}</p>
    </header>
  );
}

function MiniMetric({ k, v }: { k: string; v: string }) {
  return (
    <li className="rounded border border-hairline bg-surface-2 px-1.5 py-1">
      <div className="text-[9px] uppercase tracking-wider text-ink-muted">{k}</div>
      <div className="font-display text-[11px] font-semibold text-ink">{v}</div>
    </li>
  );
}
