import { AppShell } from "@/components/portal/AppShell";
import { getSession } from "@/lib/auth";
import { KpiTile } from "@/components/portal/KpiTile";
import { Donut } from "@/components/portal/Donut";
import { fmtDate, daysUntil, money } from "@/lib/format";

type LedgerRow = {
  product: string;
  category: "Graft" | "Dressing" | "NPWT" | "Therapy" | "Compression";
  serial: string;
  lot: string;
  udi: string;
  pkg: number;
  applied: number;
  receivedAt: string;
  expiration: string;
  status: "in-stock" | "applied" | "expired" | "recalled";
  patient?: string;
};

const LEDGER: LedgerRow[] = [
  { product: "ActiGraft+ 4×4",       category: "Graft",   serial: "AG-291847", lot: "L-2604-A", udi: "(01)00875498003420", pkg: 16, applied: 14.7, receivedAt: "2026-04-12", expiration: "2026-08-22", status: "applied",  patient: "Patricia Johnson" },
  { product: "ActiGraft+ 5×5",       category: "Graft",   serial: "AG-291902", lot: "L-2604-A", udi: "(01)00875498003437", pkg: 25, applied: 0,    receivedAt: "2026-04-12", expiration: "2026-08-22", status: "in-stock" },
  { product: "Collagen matrix 4×4",  category: "Graft",   serial: "CM-100823", lot: "L-2603-C", udi: "(01)00875498005432", pkg: 16, applied: 12.4, receivedAt: "2026-03-30", expiration: "2027-03-30", status: "applied",  patient: "Robert Williams" },
  { product: "Collagen matrix 4×4",  category: "Graft",   serial: "CM-100824", lot: "L-2603-C", udi: "(01)00875498005432", pkg: 16, applied: 0,    receivedAt: "2026-03-30", expiration: "2027-03-30", status: "in-stock" },
  { product: "Adhesion barrier 5×5", category: "Graft",   serial: "AB-552031", lot: "L-2602-X", udi: "(01)00875498005111", pkg: 25, applied: 0,    receivedAt: "2026-02-18", expiration: "2026-05-12", status: "in-stock" },
  { product: "Exosome serum 0.5ml",  category: "Therapy", serial: "EX-008713", lot: "L-2604-E", udi: "(01)00875498009012", pkg: 0,  applied: 0,    receivedAt: "2026-04-22", expiration: "2026-05-30", status: "in-stock" },
  { product: "MicroDoc canister",    category: "NPWT",    serial: "NW-220411", lot: "L-2603-N", udi: "(01)00875498002201", pkg: 0,  applied: 0,    receivedAt: "2026-03-22", expiration: "2027-03-22", status: "in-stock" },
  { product: "Foam 4×4 (10pk)",      category: "Dressing",serial: "FD-540100", lot: "L-2604-F", udi: "(01)00875498003049", pkg: 0,  applied: 0,    receivedAt: "2026-04-10", expiration: "2028-04-10", status: "in-stock" },
  { product: "Compression wrap (3L)",category: "Compression",serial:"CW-318220",lot:"L-2602-W", udi: "(01)00875498001230", pkg: 0,  applied: 0,    receivedAt: "2026-02-15", expiration: "2028-02-15", status: "in-stock" },
];

export default async function InventoryPage() {
  const session = await getSession();
  return (
    <AppShell
      title="Inventory & Graft Tracking"
      subtitle="Real-time stock, lot management, and graft traceability"
      user={{ name: "Dr. Rachel Morgan", role: session?.role ?? "clinician" }}
    >
      <section className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <KpiTile label="On-hand units" value="2,847" delta="+148 wk" tone="accent" />
        <KpiTile label="Active grafts" value="14" delta="3 in transit" />
        <KpiTile label="Expires <30d" value="23" delta="6 require swap" tone="warn" />
        <KpiTile label="Inventory value" value={money(184_320)} delta="+8% MoM" tone="accent" />
        <KpiTile label="Waste %" value="2.3%" delta="-0.4pp" tone="success" />
        <KpiTile label="UDI compliance" value="100%" delta="all units traced" tone="success" />
      </section>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-[1fr_360px]">
        <div className="card overflow-hidden">
          <div className="flex items-center justify-between border-b border-hairline bg-surface-2 px-4 py-3 text-xs">
            <div className="flex gap-1.5">
              <Chip active>Supply ledger</Chip>
              <Chip>Grafts ({LEDGER.filter((l) => l.category === "Graft").length})</Chip>
              <Chip>Dressings (1)</Chip>
              <Chip>NPWT (1)</Chip>
              <Chip>Recalls (0)</Chip>
            </div>
            <button className="btn btn-secondary">+ Receive shipment</button>
          </div>
          <div className="overflow-x-auto">
            <table className="table-base">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Serial / Lot</th>
                  <th>UDI</th>
                  <th>Received</th>
                  <th>Expiration</th>
                  <th className="text-right">Pkg / Applied (cm²)</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {LEDGER.map((r) => (
                  <tr key={r.serial} className="hover:bg-surface-2">
                    <td>
                      <div className="font-medium text-ink">{r.product}</div>
                      <div className="text-[11px] text-ink-muted">{r.category}</div>
                    </td>
                    <td>
                      <div className="font-mono text-xs">{r.serial}</div>
                      <div className="font-mono text-[10px] text-ink-muted">{r.lot}</div>
                    </td>
                    <td className="font-mono text-[11px]">{r.udi}</td>
                    <td className="whitespace-nowrap text-ink-muted">{fmtDate(r.receivedAt)}</td>
                    <td>
                      <ExpirationPill date={r.expiration} />
                    </td>
                    <td className="text-right tabular-nums">
                      {r.pkg > 0 ? `${r.applied.toFixed(1)} / ${r.pkg.toFixed(0)}` : "—"}
                    </td>
                    <td>
                      <StatusPill status={r.status} patient={r.patient} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="grid grid-cols-1 gap-3 border-t border-hairline bg-surface-2 p-4 md:grid-cols-4">
            <CategoryTile name="Dressings & bandages" count={1280} change="+4%" />
            <CategoryTile name="NPWT systems & kits" count={166} change="+1%" />
            <CategoryTile name="Collagen & matrices" count={342} change="+6%" tone="warn" />
            <CategoryTile name="Wound care supplies" count={1071} change="+2%" />
          </div>
        </div>

        <aside className="card flex flex-col gap-4 p-4">
          <header>
            <span className="eyebrow">Active graft trace</span>
            <h2 className="mt-1 font-display text-base font-semibold text-ink">ActiGraft+ 4×4</h2>
            <p className="text-xs text-ink-muted">AG-291847 · lot L-2604-A</p>
          </header>

          <ul className="space-y-2 text-xs">
            <Step at="2026-04-08" label="Manufactured by ActiGraft Inc." />
            <Step at="2026-04-12" label="Received at Midtown clinic" />
            <Step at="2026-04-29 09:14" label="Pulled from inventory · Dr. Morgan" />
            <Step at="2026-04-29 09:22" label="Applied to Patricia Johnson · 14.7 cm²" />
            <Step at="2026-04-29 09:25" label="Waste recorded: 1.3 cm² (justified)" />
            <Step at="2026-04-29 09:30" label="Linked to CLM-2026-00517" final />
          </ul>

          <div className="rounded-md border border-success/40 bg-success/10 p-3 text-xs">
            <div className="font-semibold text-success">UDI traceability complete</div>
            <p className="mt-1 text-ink-soft">
              Serial → lot → patient → claim chain auditable end-to-end.
            </p>
          </div>

          <div className="card p-3">
            <span className="eyebrow">Lot exposure</span>
            <div className="mt-2 flex items-center gap-3">
              <Donut
                size={84}
                segments={[
                  { value: 12, color: "rgb(var(--accent))" },
                  { value: 4, color: "rgb(var(--success))" },
                  { value: 0, color: "rgb(var(--danger))" },
                ]}
                centerLabel="16"
                centerSub="units"
              />
              <ul className="space-y-1 text-[11px]">
                <li className="flex items-center gap-2 text-ink-soft"><span className="h-2 w-2 rounded-full bg-accent" /> Applied · 12</li>
                <li className="flex items-center gap-2 text-ink-soft"><span className="h-2 w-2 rounded-full bg-success" /> In stock · 4</li>
                <li className="flex items-center gap-2 text-ink-soft"><span className="h-2 w-2 rounded-full bg-danger" /> Recalled · 0</li>
              </ul>
            </div>
          </div>
        </aside>
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

function ExpirationPill({ date }: { date: string }) {
  const days = daysUntil(date);
  if (days < 0) return <span className="pill pill-danger">Expired {-days}d</span>;
  if (days < 30) return <span className="pill pill-warn">{days}d left</span>;
  return <span className="pill pill-neutral">{fmtDate(date)}</span>;
}

function StatusPill({ status, patient }: { status: LedgerRow["status"]; patient?: string }) {
  if (status === "applied") {
    return (
      <span className="flex flex-col gap-0.5">
        <span className="pill pill-accent">Applied</span>
        {patient && <span className="text-[11px] text-ink-muted">{patient}</span>}
      </span>
    );
  }
  if (status === "in-stock") return <span className="pill pill-success">In stock</span>;
  if (status === "expired") return <span className="pill pill-danger">Expired</span>;
  return <span className="pill pill-danger">Recalled</span>;
}

function CategoryTile({ name, count, change, tone = "accent" }: { name: string; count: number; change: string; tone?: "accent" | "warn" }) {
  return (
    <div className="rounded-md border border-hairline bg-surface p-3">
      <p className="text-[11px] uppercase tracking-[0.14em] text-ink-muted">{name}</p>
      <p className="mt-2 font-display text-2xl font-semibold text-ink">{count.toLocaleString()}</p>
      <p className={`mt-0.5 text-[11px] ${tone === "warn" ? "text-warn" : "text-success"}`}>
        {change} vs last mo
      </p>
    </div>
  );
}

function Step({ at, label, final }: { at: string; label: string; final?: boolean }) {
  return (
    <li className="flex items-start gap-2">
      <span className={`mt-1 inline-block h-2 w-2 shrink-0 rounded-full ${final ? "bg-success" : "bg-accent"}`} />
      <div>
        <div className="font-mono text-[10px] text-ink-muted">{at}</div>
        <div className="text-ink-soft">{label}</div>
      </div>
    </li>
  );
}
