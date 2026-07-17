"use client";

import { useMemo, useState } from "react";
import { KpiTile } from "@/components/portal/KpiTile";
import { CLAIMS } from "@/lib/sample";
import { Chip, ViewHeader } from "./shared";

const STATUSES = ["all", "paid", "pending", "denied", "appeal"] as const;

/** Claims with live status filters; expanding a claim shows its evidence bundle. */
export function ClaimsView() {
  const [status, setStatus] = useState<(typeof STATUSES)[number]>("all");
  const [openId, setOpenId] = useState<string | null>(CLAIMS[0]!.id);

  const rows = useMemo(
    () => CLAIMS.filter((c) => status === "all" || c.status === status),
    [status],
  );

  return (
    <div className="space-y-4">
      <ViewHeader
        title="Claims & Compliance"
        sub="Reimbursement visibility with audit readiness built in — click a claim to open its evidence bundle"
      />
      <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-4">
        <KpiTile label="Compliance score" value="96%" delta="audit-ready" tone="success" />
        <KpiTile label="April paid" value="$298,400" delta="88.5% of billed" tone="accent" />
        <KpiTile label="Pending" value="$34,120" delta="10.1%" />
        <KpiTile label="Avg days to pay" value="14.2" delta="−1.8d vs Q1" tone="success" />
      </div>

      <div className="flex flex-wrap gap-1.5">
        {STATUSES.map((s) => (
          <Chip key={s} active={status === s} onClick={() => setStatus(s)}>
            {s === "all" ? `All (${CLAIMS.length})` : `${s} (${CLAIMS.filter((c) => c.status === s).length})`}
          </Chip>
        ))}
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
            {rows.map((c) => (
              <FragmentRow
                key={c.id}
                claim={c}
                open={openId === c.id}
                onToggle={() => setOpenId(openId === c.id ? null : c.id)}
              />
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

function FragmentRow({
  claim,
  open,
  onToggle,
}: {
  claim: (typeof CLAIMS)[number];
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <>
      <tr
        onClick={onToggle}
        className={`cursor-pointer ${open ? "bg-accent/5" : "hover:bg-surface-2"}`}
        title="Open evidence bundle"
      >
        <td className="font-mono text-[11px]">
          {claim.id.replace("CLM-2026-", "…")}
          <span className={`ml-1.5 inline-block text-accent transition-transform ${open ? "rotate-90" : ""}`}>▸</span>
        </td>
        <td className="whitespace-nowrap text-ink-soft">{claim.patient}</td>
        <td className="font-mono text-xs">{claim.cpt}</td>
        <td className="text-ink-muted">{claim.payer}</td>
        <td className="text-right tabular-nums">${claim.amount.toFixed(2)}</td>
        <td>
          <span
            className={`pill ${
              claim.status === "paid"
                ? "pill-success"
                : claim.status === "denied"
                  ? "pill-danger"
                  : claim.status === "appeal"
                    ? "pill-warn"
                    : "pill-accent"
            }`}
          >
            {claim.status}
          </span>
        </td>
      </tr>
      {open && (
        <tr className="bg-surface-2/60">
          <td colSpan={6} className="!p-3">
            <div className="grid gap-2 text-[11px] sm:grid-cols-3">
              <div className="rounded border border-hairline bg-surface p-2.5">
                <p className="font-semibold text-ink">Timeline</p>
                <p className="mt-1 text-ink-soft">
                  Submitted {claim.submitted}
                  {claim.adjudicated ? ` · adjudicated ${claim.adjudicated}` : " · awaiting adjudication"}
                  {claim.paid !== null && claim.paid > 0 ? ` · paid $${claim.paid.toFixed(2)}` : ""}
                </p>
              </div>
              <div className="rounded border border-hairline bg-surface p-2.5">
                <p className="font-semibold text-ink">Evidence bundle</p>
                <p className="mt-1 text-ink-soft">
                  3D measurement ✓ · top-view diagram ✓ · signed note ✓ · UDI/lot ✓
                </p>
              </div>
              <div className="rounded border border-hairline bg-surface p-2.5">
                <p className="font-semibold text-ink">Defense posture</p>
                <p className="mt-1 text-ink-soft">
                  {claim.status === "denied"
                    ? "Appeal drafted — instrument-derived dimensions attached as objective proof."
                    : "Every billed dimension traces to a content-hashed capture. Audit-ready."}
                </p>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
