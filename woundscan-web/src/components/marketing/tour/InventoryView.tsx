"use client";

import { useMemo, useState } from "react";
import { KpiTile } from "@/components/portal/KpiTile";
import { Chip, ViewHeader } from "./shared";

type Row = {
  product: string;
  category: "Graft" | "Therapy" | "NPWT" | "Dressing";
  serial: string;
  lot: string;
  udi: string;
  exp: string;
  status: "applied" | "in-stock" | "expiring";
  patient?: string;
  trace: string[];
};

const LEDGER: Row[] = [
  {
    product: "ActiGraft+ 4×4", category: "Graft", serial: "AG-291847", lot: "L-2604-A",
    udi: "(01)00875498003420", exp: "2026-08-22", status: "applied", patient: "P. Johnson",
    trace: ["Manufactured 04-08", "Received Midtown 04-12", "Assigned P. Johnson 04-28", "Applied 14.7 cm² 04-29", "Claim CLM-00517 04-30"],
  },
  {
    product: "ActiGraft+ 5×5", category: "Graft", serial: "AG-291902", lot: "L-2604-A",
    udi: "(01)00875498003437", exp: "2026-08-22", status: "in-stock",
    trace: ["Manufactured 04-08", "Received Midtown 04-12", "In stock · reserved for none"],
  },
  {
    product: "Collagen matrix 4×4", category: "Graft", serial: "CM-100823", lot: "L-2603-C",
    udi: "(01)00875498005432", exp: "2027-03-30", status: "applied", patient: "R. Williams",
    trace: ["Manufactured 03-18", "Received Westside 03-30", "Assigned R. Williams 04-26", "Applied 12.4 cm² 04-28", "Claim CLM-00516 04-30"],
  },
  {
    product: "Adhesion barrier 5×5", category: "Graft", serial: "AB-552031", lot: "L-2602-X",
    udi: "(01)00875498005111", exp: "2026-05-12", status: "expiring",
    trace: ["Manufactured 02-02", "Received Bayonne 02-18", "⚠ Expires 05-12 — swap recommended"],
  },
  {
    product: "Exosome serum 0.5ml", category: "Therapy", serial: "EX-008713", lot: "L-2604-E",
    udi: "(01)00875498009012", exp: "2026-05-30", status: "in-stock",
    trace: ["Manufactured 04-15", "Cold-chain received 04-22 · 2–8°C verified"],
  },
  {
    product: "MicroDoc canister", category: "NPWT", serial: "NW-220411", lot: "L-2603-N",
    udi: "(01)00875498002201", exp: "2027-03-22", status: "in-stock",
    trace: ["Manufactured 03-10", "Received Midtown 03-22"],
  },
  {
    product: "Foam 4×4 (10pk)", category: "Dressing", serial: "FD-540100", lot: "L-2604-F",
    udi: "(01)00875498003049", exp: "2028-04-10", status: "in-stock",
    trace: ["Manufactured 03-28", "Received Midtown 04-10"],
  },
];

const CATS = ["All", "Graft", "Therapy", "NPWT", "Dressing"] as const;

/** UDI ledger with live category filters; selecting a row drives the trace panel. */
export function InventoryView() {
  const [cat, setCat] = useState<(typeof CATS)[number]>("All");
  const [selectedSerial, setSelectedSerial] = useState(LEDGER[0]!.serial);

  const rows = useMemo(() => LEDGER.filter((r) => cat === "All" || r.category === cat), [cat]);
  const selected = LEDGER.find((r) => r.serial === selectedSerial) ?? LEDGER[0]!;

  return (
    <div className="space-y-4">
      <ViewHeader
        title="Inventory & Graft Tracking"
        sub="Real-time stock, lot management, graft traceability — click a row to trace it"
      />
      <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-4">
        <KpiTile label="On-hand units" value="2,847" delta="+148 this week" tone="accent" />
        <KpiTile label="Expires <30d" value="23" delta="6 require swap" tone="warn" />
        <KpiTile label="Waste" value="2.3%" delta="−0.4pp MoM" tone="success" />
        <KpiTile label="UDI compliance" value="100%" delta="all units traced" tone="success" />
      </div>

      <div className="flex flex-wrap gap-1.5">
        {CATS.map((c) => (
          <Chip key={c} active={cat === c} onClick={() => setCat(c)}>
            {c === "All" ? `All (${LEDGER.length})` : `${c} (${LEDGER.filter((r) => r.category === c).length})`}
          </Chip>
        ))}
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
            {rows.map((r) => (
              <tr
                key={r.serial}
                onClick={() => setSelectedSerial(r.serial)}
                className={`cursor-pointer ${r.serial === selectedSerial ? "bg-accent/5" : "hover:bg-surface-2"}`}
                title="Trace this unit"
              >
                <td>
                  <span className="font-medium text-ink">{r.product}</span>
                  {r.serial === selectedSerial && <span className="ml-1.5 text-accent">◀</span>}
                  <div className="text-[10px] text-ink-muted">{r.category}</div>
                </td>
                <td>
                  <div className="font-mono text-xs">{r.serial}</div>
                  <div className="font-mono text-[10px] text-ink-muted">{r.lot}</div>
                </td>
                <td className="font-mono text-[11px]">{r.udi}</td>
                <td className="whitespace-nowrap text-ink-muted">{r.exp}</td>
                <td>
                  {r.status === "applied" ? (
                    <span className="pill pill-accent">applied · {r.patient}</span>
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
        <span className="eyebrow">
          Unit trace · {selected.product} · {selected.serial}
        </span>
        <ol className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-ink-soft">
          {selected.trace.map((s, i, arr) => (
            <li key={s} className="flex items-center gap-2">
              <span className={`rounded border px-2 py-1 ${s.startsWith("⚠") ? "border-warn/50 bg-warn/5 text-warn" : "border-hairline bg-surface"}`}>
                {s}
              </span>
              {i < arr.length - 1 && <span aria-hidden className="text-accent">→</span>}
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
