"use client";

import { useMemo, useState } from "react";
import { ORDERS } from "@/lib/sample";
import { fmtDate, money } from "@/lib/format";
import { KpiTile } from "@/components/portal/KpiTile";

const CATALOG = [
  { name: "ActiGraft+ 4×4", code: "AG-4404", price: 1245.00, stock: "in stock" },
  { name: "Collagen wound matrix 4×4", code: "COL-4404", price: 206.25, stock: "in stock" },
  { name: "UltraMist therapy session", code: "UM-SESS", price: 365.00, stock: "scheduled" },
  { name: "Adhesion barrier 5×5", code: "AB-5505", price: 1690.00, stock: "low (3)" },
  { name: "Compression wrap (3 layer)", code: "CW-3L", price: 14.55, stock: "in stock" },
  { name: "Foam dressing 4×4 (10pk)", code: "FD-4410", price: 64.50, stock: "in stock" },
  { name: "Exosome serum 0.5ml", code: "EX-05ML", price: 2150.00, stock: "low (2)" },
  { name: "MicroDoc NPWT canister", code: "NPWT-CAN", price: 49.60, stock: "in stock" },
] as const;

const FILTERS = ["Recent", "Open", "Approved", "Templates"] as const;
type Filter = (typeof FILTERS)[number];

export function OrdersBoard() {
  const [filter, setFilter] = useState<Filter>("Recent");
  const [selectedId, setSelectedId] = useState<string>(ORDERS[0]?.id ?? "");
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    let rows = ORDERS;
    if (filter === "Open") rows = rows.filter((o) => o.status === "review" || o.status === "approved");
    if (filter === "Approved") rows = rows.filter((o) => o.status === "approved");
    if (search.trim()) {
      const q = search.toLowerCase();
      rows = rows.filter(
        (o) => o.id.toLowerCase().includes(q) || o.patient.toLowerCase().includes(q) || o.product.toLowerCase().includes(q),
      );
    }
    return rows;
  }, [filter, search]);

  const selected = ORDERS.find((o) => o.id === selectedId) ?? ORDERS[0]!;

  return (
    <>
      <section className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <KpiTile label="Total orders" value="142" delta="+18 wk" tone="accent" />
        <KpiTile label="Order volume (MTD)" value={money(64_275)} delta="+12% MoM" tone="accent" />
        <KpiTile label="Active deliveries" value="8" delta="ETA today" />
        <KpiTile label="In transit" value="92" delta="across all sites" />
        <KpiTile label="Backorders" value="3" delta="2 alternates" tone="warn" />
        <KpiTile label="Delivery on-time" value="98.2%" delta="+0.4pp" tone="success" />
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
                placeholder="Filter orders…"
                className="input w-full md:w-56"
              />
              <button className="btn btn-primary whitespace-nowrap">+ New</button>
            </div>
          </div>

          {/* Desktop table */}
          <div className="hidden overflow-x-auto md:block">
            <table className="table-base">
              <thead>
                <tr>
                  <th>Order</th>
                  <th>Patient</th>
                  <th>Product</th>
                  <th className="text-right">Units</th>
                  <th className="text-right">Amount</th>
                  <th>Status</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((o) => (
                  <tr
                    key={o.id}
                    className={`cursor-pointer transition ${o.id === selectedId ? "bg-accent/10" : "hover:bg-surface-2"}`}
                    onClick={() => setSelectedId(o.id)}
                  >
                    <td className="font-mono text-xs">{o.id}</td>
                    <td>{o.patient}</td>
                    <td className="max-w-[220px] truncate" title={o.product}>{o.product}</td>
                    <td className="text-right tabular-nums">{o.units}</td>
                    <td className="text-right tabular-nums">{money(o.amount)}</td>
                    <td><OrderPill status={o.status} /></td>
                    <td className="whitespace-nowrap text-ink-muted">{fmtDate(o.date)}</td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr><td colSpan={7} className="p-8 text-center text-ink-muted">No matching orders</td></tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Mobile cards */}
          <ul className="divide-y divide-hairline md:hidden">
            {filtered.map((o) => (
              <li
                key={o.id}
                onClick={() => setSelectedId(o.id)}
                className={`cursor-pointer p-3 ${o.id === selectedId ? "bg-accent/10" : ""}`}
              >
                <div className="flex items-baseline justify-between">
                  <span className="font-mono text-xs text-ink-muted">{o.id}</span>
                  <OrderPill status={o.status} />
                </div>
                <div className="mt-1 font-medium text-ink">{o.patient}</div>
                <div className="text-xs text-ink-muted">{o.product}</div>
                <div className="mt-1 flex items-baseline justify-between text-xs">
                  <span className="text-ink-muted">{fmtDate(o.date)} · {o.units}u</span>
                  <span className="font-semibold text-ink">{money(o.amount)}</span>
                </div>
              </li>
            ))}
          </ul>

          <div className="border-t border-hairline p-4">
            <h3 className="font-display text-sm font-semibold text-ink">Product catalog</h3>
            <p className="text-xs text-ink-muted">Tap to add to the active patient&apos;s order.</p>
            <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-4">
              {CATALOG.map((c) => (
                <button
                  key={c.code}
                  type="button"
                  className="rounded-md border border-hairline bg-surface p-3 text-left text-xs transition hover:border-accent/60 hover:bg-accent/5"
                >
                  <div className="font-medium text-ink">{c.name}</div>
                  <div className="font-mono text-[10px] text-ink-muted">{c.code}</div>
                  <div className="mt-2 flex items-center justify-between">
                    <span className="font-semibold text-ink">{money(c.price)}</span>
                    <span className={`pill ${c.stock.startsWith("low") ? "pill-warn" : c.stock === "scheduled" ? "pill-accent" : "pill-success"}`}>
                      {c.stock}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        <OrderDetail order={selected} />
      </div>
    </>
  );
}

function OrderPill({ status }: { status: "shipped" | "delivered" | "in-transit" | "approved" | "review" }) {
  const map = {
    shipped: "pill pill-accent",
    delivered: "pill pill-success",
    "in-transit": "pill pill-accent",
    approved: "pill pill-success",
    review: "pill pill-warn",
  } as const;
  return <span className={map[status]}>{status.replace("-", " ")}</span>;
}

function OrderDetail({
  order,
}: {
  order: { id: string; patient: string; product: string; units: number; amount: number; status: string; tracking?: string; date: string };
}) {
  return (
    <aside className="card flex flex-col gap-4 p-4">
      <header className="flex items-start justify-between gap-2">
        <div>
          <span className="eyebrow">Order alert</span>
          <h2 className="mt-1 font-display text-base font-semibold text-ink">{order.id}</h2>
          <p className="text-xs text-ink-muted">{order.patient}</p>
        </div>
        <span className="pill pill-accent">{order.status}</span>
      </header>

      <ul className="space-y-2 text-sm">
        <Line label={order.product} qty={order.units} amount={order.amount} />
      </ul>

      <div className="border-t border-hairline pt-3">
        <Row label="Subtotal" value={money(order.amount)} />
        <Row label="Shipping" value={money(0)} />
        <Row label="Tax (est)" value={money(0)} />
        <Row label="Total" value={money(order.amount)} bold />
      </div>

      <div className="rounded-md border border-hairline bg-surface-2 p-3 text-[11px] text-ink-soft">
        <div className="flex items-center justify-between">
          <span>Tracking</span>
          <span className="font-mono text-ink">{order.tracking ?? "—"}</span>
        </div>
        <div className="mt-1 flex items-center justify-between">
          <span>Carrier</span>
          <span className="text-ink">FedEx Priority</span>
        </div>
        <div className="mt-1 flex items-center justify-between">
          <span>ETA</span>
          <span className="text-ink">{fmtDate(order.date)} 10:30</span>
        </div>
      </div>

      <button className="btn btn-primary justify-center">Reorder</button>
      <button className="btn btn-secondary justify-center">View full tracking</button>

      <div className="rounded-md border border-success/40 bg-success/10 p-3 text-xs text-success">
        UDI logged · linked to claim CLM-2026-00517
      </div>
    </aside>
  );
}

function Line({ label, qty, amount }: { label: string; qty: number; amount: number }) {
  return (
    <li className="flex items-baseline justify-between border-b border-hairline pb-2">
      <div>
        <div className="text-ink">{label}</div>
        <div className="text-[11px] text-ink-muted">qty {qty}</div>
      </div>
      <div className="font-medium tabular-nums text-ink">{money(amount)}</div>
    </li>
  );
}

function Row({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <div className={`flex justify-between text-sm ${bold ? "mt-1.5 font-semibold text-ink" : "text-ink-soft"}`}>
      <span>{label}</span>
      <span className="tabular-nums">{value}</span>
    </div>
  );
}
