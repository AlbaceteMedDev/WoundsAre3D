import { AppShell } from "@/components/portal/AppShell";
import { getSession } from "@/lib/auth";
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
];

export default async function OrdersPage() {
  const session = await getSession();
  return (
    <AppShell
      title="Orders"
      subtitle="Place orders, track shipments, and manage fulfillment"
      user={{ name: "Dr. Rachel Morgan", role: session?.role ?? "clinician" }}
    >
      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <KpiTile label="Open orders" value="15" delta="3 over 48h" tone="warn" />
        <KpiTile label="In transit" value="6" delta="ETA today" />
        <KpiTile label="Delivered (mo)" value="24" delta="+5 vs Mar" tone="success" />
        <KpiTile label="Spend (mo)" value={money(48_220)} delta="89% on plan" tone="accent" />
      </section>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-[1fr_360px]">
        <div className="card overflow-hidden">
          <div className="flex items-center justify-between border-b border-hairline bg-surface-2 px-4 py-3 text-xs">
            <div className="flex gap-1.5">
              <Chip active>Recent ({ORDERS.length})</Chip>
              <Chip>Open (15)</Chip>
              <Chip>Approved</Chip>
              <Chip>Templates</Chip>
            </div>
            <button className="btn btn-primary">+ New order</button>
          </div>
          <div className="overflow-x-auto">
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
                {ORDERS.map((o) => (
                  <tr key={o.id} className="hover:bg-surface-2">
                    <td className="font-mono text-xs">{o.id}</td>
                    <td>{o.patient}</td>
                    <td className="max-w-[220px] truncate" title={o.product}>{o.product}</td>
                    <td className="text-right tabular-nums">{o.units}</td>
                    <td className="text-right tabular-nums">{money(o.amount)}</td>
                    <td><OrderPill status={o.status} /></td>
                    <td className="whitespace-nowrap text-ink-muted">{fmtDate(o.date)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="border-t border-hairline p-4">
            <h3 className="font-display text-sm font-semibold text-ink">Product catalog</h3>
            <p className="text-xs text-ink-muted">Add to cart for the active patient case.</p>
            <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-4">
              {CATALOG.map((c) => (
                <div key={c.code} className="rounded-md border border-hairline bg-surface p-3 text-xs">
                  <div className="font-medium text-ink">{c.name}</div>
                  <div className="font-mono text-[10px] text-ink-muted">{c.code}</div>
                  <div className="mt-2 flex items-center justify-between">
                    <span className="font-semibold text-ink">{money(c.price)}</span>
                    <span className={`pill ${c.stock.startsWith("low") ? "pill-warn" : c.stock === "scheduled" ? "pill-accent" : "pill-success"}`}>
                      {c.stock}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <OrderSummary />
      </div>
    </AppShell>
  );
}

function Chip({ children, active }: { children: React.ReactNode; active?: boolean }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-medium ${
        active ? "bg-accent/15 text-accent" : "border border-hairline text-ink-soft"
      }`}
    >
      {children}
    </span>
  );
}

function OrderPill({ status }: { status: "shipped" | "delivered" | "in-transit" | "approved" | "review" }) {
  const map = {
    shipped: "pill pill-accent",
    delivered: "pill pill-success",
    "in-transit": "pill pill-accent",
    approved: "pill pill-success",
    review: "pill pill-warn",
  };
  return <span className={map[status]}>{status.replace("-", " ")}</span>;
}

function OrderSummary() {
  return (
    <aside className="card flex flex-col gap-4 p-4">
      <header>
        <span className="eyebrow">Order summary</span>
        <h2 className="mt-1 font-display text-base font-semibold text-ink">AO-291 — Patricia Johnson</h2>
        <p className="text-xs text-ink-muted">Dr. Morgan · Midtown clinic</p>
      </header>

      <ul className="space-y-2 text-sm">
        <Line label="ActiGraft+ 4×4 (AG-4404)" qty={1} amount={1245.00} />
        <Line label="Collagen wound matrix 4×4" qty={2} amount={412.50} />
        <Line label="Compression wrap (3 layer)" qty={6} amount={87.30} />
      </ul>

      <div className="border-t border-hairline pt-3">
        <Row label="Subtotal" value={money(1744.80)} />
        <Row label="Shipping" value={money(0.00)} />
        <Row label="Tax (est)" value={money(0.00)} />
        <Row label="Total" value={money(1744.80)} bold />
      </div>

      <button className="btn btn-primary justify-center">Reorder</button>
      <button className="btn btn-secondary justify-center">View Full Tracking</button>

      <div className="mt-2 rounded-md border border-hairline bg-surface-2 p-3 text-[11px] text-ink-muted">
        <div>Tracking 9400-1112-0253 · FedEx Priority</div>
        <div className="mt-1">Picked up Apr 30 06:14 · ETA Apr 30 10:30</div>
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
