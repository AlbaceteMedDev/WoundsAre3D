"use client";

import { useEffect, useRef, useState } from "react";
import { KpiTile } from "@/components/portal/KpiTile";
import { Chip, ViewHeader } from "./shared";

const TABS = ["Audit log", "Products", "ML metrics", "Users"] as const;

const AUDIT = [
  { at: "09:41:07", action: "note.sign", user: "dr.morgan", resource: "note/PJ-v6", hash: "6b1f…9c2e" },
  { at: "09:12:44", action: "claim.submit", user: "billing-bot", resource: "CLM-2026-00517", hash: "e42a…77b1" },
  { at: "08:58:02", action: "measurement.create", user: "np.adler", resource: "msr/MC-s3-v9", hash: "91cd…04af" },
  { at: "08:31:19", action: "order.approve", user: "dr.romero", resource: "AO-291", hash: "b7f3…d210" },
  { at: "08:05:56", action: "inventory.receive", user: "ops.chen", resource: "lot/L-2604-A", hash: "22e9…8c44" },
  { at: "07:44:31", action: "user.login", user: "dr.morgan", resource: "session/totp", hash: "f0a1…3b7d" },
];

const PRODUCTS = [
  { id: "PRD-014", name: "ActiGraft+ 4×4", mfr: "ActiGraft Inc.", overlap: 0.5, sizes: "16 / 25 / 36", ind: "DFU, VLU" },
  { id: "PRD-015", name: "ActiGraft+ 5×5", mfr: "ActiGraft Inc.", overlap: 0.5, sizes: "25 / 36", ind: "DFU, VLU" },
  { id: "PRD-021", name: "Collagen matrix 4×4", mfr: "DermaCol", overlap: 0.3, sizes: "16 / 25", ind: "DFU, PI, dehiscence" },
  { id: "PRD-029", name: "Adhesion barrier 5×5", mfr: "SurgiTech", overlap: 0.4, sizes: "25", ind: "Post-surgical" },
];

const USERS = [
  { name: "Dr. Rachel Morgan", role: "clinician", totp: true, last: "today 07:44" },
  { name: "Dr. Luis Romero", role: "clinician", totp: true, last: "today 07:58" },
  { name: "NP Dana Adler", role: "clinician", totp: true, last: "today 08:12" },
  { name: "G. Albacete", role: "admin", totp: true, last: "yesterday" },
  { name: "Reviewer (payer)", role: "reviewer", totp: true, last: "Apr 22" },
];

/** Admin console — sub-tabs, with a live tamper-evidence verification demo. */
export function AdminView() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Audit log");
  const [verified, setVerified] = useState(0); // rows verified so far
  const [running, setRunning] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const verify = () => {
    setVerified(0);
    setRunning(true);
  };

  useEffect(() => {
    if (!running) return;
    timer.current = setInterval(() => {
      setVerified((v) => {
        if (v >= AUDIT.length) {
          setRunning(false);
          return v;
        }
        return v + 1;
      });
    }, 260);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [running]);

  const chainIntact = !running && verified >= AUDIT.length;

  return (
    <div className="space-y-4">
      <ViewHeader title="Admin Console" sub="Products, audit chain, model health, access control" />

      <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-4">
        <KpiTile label="Audit entries" value="4,183" delta="hash-linked chain" tone="accent" />
        <KpiTile label="Products" value="24" delta="versioned IFU data" />
        <KpiTile label="Model drift alerts" value="0" delta="baselines stable" tone="success" />
        <KpiTile label="Users w/ MFA" value="100%" delta="TOTP enforced" tone="success" />
      </div>

      <div className="flex flex-wrap gap-1.5">
        {TABS.map((t) => (
          <Chip key={t} active={tab === t} onClick={() => setTab(t)}>
            {t}
          </Chip>
        ))}
      </div>

      {tab === "Audit log" && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs text-ink-soft">
              Every write is hash-linked to the previous entry. Tampering breaks the chain —
              prove it:
            </p>
            <button type="button" onClick={verify} disabled={running} className="btn btn-primary text-xs disabled:opacity-60">
              {running ? "Verifying…" : chainIntact ? "Verify again" : "Verify chain integrity"}
            </button>
          </div>
          {chainIntact && (
            <p className="rounded border-l-2 border-success/60 bg-success/5 px-3 py-2 font-mono text-[11px] text-success">
              verify_chain() → 4,183 entries · 0 breaks · chain intact ✓
            </p>
          )}
          <div className="card overflow-x-auto !p-0">
            <table className="table-base">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Action</th>
                  <th>User</th>
                  <th>Resource</th>
                  <th>Hash</th>
                  <th>Link</th>
                </tr>
              </thead>
              <tbody className="font-mono text-xs">
                {AUDIT.map((a, i) => (
                  <tr key={a.hash} className={i < verified ? "bg-success/5" : "hover:bg-surface-2"}>
                    <td>{a.at}</td>
                    <td className="text-accent">{a.action}</td>
                    <td>{a.user}</td>
                    <td>{a.resource}</td>
                    <td className="text-ink-muted">{a.hash}</td>
                    <td>{i < verified ? <span className="text-success">✓ linked</span> : <span className="text-ink-muted">·</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "Products" && (
        <div className="card overflow-x-auto !p-0">
          <table className="table-base">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Manufacturer</th>
                <th className="text-right">Overlap δ (cm)</th>
                <th>Stock sizes (cm²)</th>
                <th>Indications</th>
              </tr>
            </thead>
            <tbody>
              {PRODUCTS.map((p) => (
                <tr key={p.id} className="hover:bg-surface-2">
                  <td className="font-mono text-xs">{p.id}</td>
                  <td className="font-medium text-ink">{p.name}</td>
                  <td className="text-ink-soft">{p.mfr}</td>
                  <td className="text-right tabular-nums">{p.overlap.toFixed(1)}</td>
                  <td className="font-mono text-xs">{p.sizes}</td>
                  <td className="text-ink-muted">{p.ind}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "ML metrics" && (
        <div className="grid gap-3 lg:grid-cols-3">
          {[
            { k: "Boundary IoU (rolling)", v: "0.912", d: "baseline 0.905 · stable" },
            { k: "Tissue macro F1", v: "0.874", d: "baseline 0.871 · stable" },
            { k: "Probe detection recall", v: "0.953", d: "baseline 0.949 · stable" },
          ].map((m) => (
            <div key={m.k} className="card p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-muted">{m.k}</p>
              <p className="mt-2 font-display text-3xl font-semibold text-ink">{m.v}</p>
              <p className="mt-1 text-[11px] text-success">{m.d}</p>
            </div>
          ))}
          <div className="card p-4 lg:col-span-3">
            <span className="eyebrow">Drift policy</span>
            <p className="mt-1.5 text-xs leading-relaxed text-ink-soft">
              Alerts fire when a model&rsquo;s rolling validation metric drops more than 3% from
              its deployed baseline. Weights are versioned with every measurement, so any
              historical report can be reproduced with the exact model that generated it.
            </p>
          </div>
        </div>
      )}

      {tab === "Users" && (
        <div className="card overflow-x-auto !p-0">
          <table className="table-base">
            <thead>
              <tr>
                <th>User</th>
                <th>Role</th>
                <th>MFA</th>
                <th>Last sign-in</th>
              </tr>
            </thead>
            <tbody>
              {USERS.map((u) => (
                <tr key={u.name} className="hover:bg-surface-2">
                  <td className="font-medium text-ink">{u.name}</td>
                  <td>
                    <span className={`pill ${u.role === "admin" ? "pill-accent" : u.role === "reviewer" ? "pill-neutral" : "pill-success"}`}>
                      {u.role}
                    </span>
                  </td>
                  <td>{u.totp ? <span className="text-success">TOTP ✓</span> : "—"}</td>
                  <td className="text-ink-muted">{u.last}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
