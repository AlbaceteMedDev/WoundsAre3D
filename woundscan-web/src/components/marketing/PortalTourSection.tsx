"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { Reveal } from "./Reveal";
import { DashboardView } from "./tour/DashboardView";
import { PatientsView } from "./tour/PatientsView";
import { WoundRecordView } from "./tour/WoundRecordView";
import { ScanView } from "./tour/ScanView";
import { NotesView } from "./tour/NotesView";
import { InventoryView } from "./tour/InventoryView";
import { ClaimsView } from "./tour/ClaimsView";
import { ReportsView } from "./tour/ReportsView";
import { RoutesView } from "./tour/RoutesView";
import { AdminView } from "./tour/AdminView";
import type { TourNavigate, TourView } from "./tour/shared";

const NAV: Array<{ key: TourView; label: string; icon: string }> = [
  { key: "dashboard", label: "Dashboard", icon: "▦" },
  { key: "patients", label: "Patients", icon: "☺" },
  { key: "wound", label: "Wound record", icon: "◉" },
  { key: "scan", label: "3D Scan Studio", icon: "✦" },
  { key: "notes", label: "Notes", icon: "✎" },
  { key: "inventory", label: "Inventory", icon: "◇" },
  { key: "claims", label: "Claims & compliance", icon: "✓" },
  { key: "reports", label: "Reports", icon: "≣" },
  { key: "routes", label: "Routes", icon: "↳" },
  { key: "admin", label: "Admin", icon: "⚙" },
];

/**
 * Interactive portal tour: the full simulated product. Every view of the
 * real portal is represented — same design system, same chart components,
 * synthetic data — plus the genuine 3D scan workspace mounted as a tab.
 * All navigation, filters, drill-downs, signing, routing, and audit
 * verification below are live client-side interactions.
 */
export function PortalTourSection() {
  const [view, setView] = useState<TourView>("dashboard");
  const [patientId, setPatientId] = useState("p1");

  const go = useCallback<TourNavigate>((v, pid) => {
    if (pid) setPatientId(pid);
    setView(v);
  }, []);

  return (
    <section id="portal" className="relative scroll-mt-20 py-20 md:py-28">
      <div className="mk-section">
        <Reveal>
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <span className="eyebrow">Inside the portal — you&rsquo;re driving</span>
              <h2 className="mk-h2 mt-3">
                The whole wound service line. <span className="text-gradient">One login.</span>
              </h2>
              <p className="mk-lead">
                This isn&rsquo;t a slideshow — it&rsquo;s the software. Ten working views:
                EHR-grade patient tracking, audit-safe documentation, the real 3D scan studio,
                UDI-traceable inventory, claims, analytics, route planning, and the admin console
                with a live tamper-evidence check. Click anything.
              </p>
            </div>
            <span className="mk-chip">fully interactive · synthetic data · no PHI</span>
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
                {/* Mobile: 2-col grid so all ten views are visible and tappable.
                    md+: vertical sidebar. */}
                <nav
                  className="grid grid-cols-2 gap-1 p-2 md:flex md:flex-col md:p-3"
                  aria-label="Portal views"
                >
                  {NAV.map((n) => (
                    <button
                      key={n.key}
                      type="button"
                      onClick={() => go(n.key)}
                      aria-pressed={view === n.key}
                      className={`flex items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-[13px] font-medium leading-tight transition md:px-3 md:text-sm ${
                        view === n.key
                          ? "bg-accent/10 text-accent"
                          : "text-ink-soft hover:bg-surface hover:text-ink"
                      }`}
                    >
                      <span aria-hidden className="w-4 shrink-0 text-center">{n.icon}</span>
                      {n.label}
                    </button>
                  ))}
                </nav>
              </aside>

              {/* Active view — natural flow on mobile (no trapped scroll),
                  capped scroll box on desktop. */}
              <div className="min-w-0 bg-bg/40 p-4 md:max-h-[640px] md:overflow-y-auto md:p-5">
                {view === "dashboard" && <DashboardView go={go} />}
                {view === "patients" && <PatientsView go={go} />}
                {view === "wound" && <WoundRecordView patientId={patientId} go={go} />}
                {view === "scan" && <ScanView />}
                {view === "notes" && <NotesView />}
                {view === "inventory" && <InventoryView />}
                {view === "claims" && <ClaimsView />}
                {view === "reports" && <ReportsView />}
                {view === "routes" && <RoutesView />}
                {view === "admin" && <AdminView />}
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
              href="mailto:gabe@stratametricai.com?subject=StrataMetric%20portal%20walkthrough"
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
