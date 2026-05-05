import { AppShell } from "@/components/portal/AppShell";
import { getSession } from "@/lib/auth";
import { KpiTile } from "@/components/portal/KpiTile";

type Stop = {
  seq: number;
  arrive: string;
  depart: string;
  patient: string;
  address: string;
  visit: string;
  windowOk: boolean;
  drive: string;
  status: "next" | "scheduled" | "complete" | "delay";
};

const STOPS: Stop[] = [
  { seq: 1, arrive: "08:30", depart: "09:00", patient: "Patricia Johnson",  address: "742 Park Ave, Orlando FL",        visit: "Wound check + ActiGraft+ q14d",       windowOk: true,  drive: "—",        status: "complete" },
  { seq: 2, arrive: "09:25", depart: "09:55", patient: "James Carter",      address: "1208 Grand St, Winter Park FL",   visit: "Surgical follow-up",                  windowOk: true,  drive: "12 min",   status: "complete" },
  { seq: 3, arrive: "10:20", depart: "10:50", patient: "Robert Williams",   address: "514 Edgewater Dr, Orlando FL",    visit: "VLU compression check",               windowOk: true,  drive: "14 min",   status: "next"     },
  { seq: 4, arrive: "11:30", depart: "12:00", patient: "Margaret Chen",     address: "918 Lakeview Pkwy, Maitland FL",  visit: "Sacral PI · debridement",             windowOk: false, drive: "22 min",   status: "scheduled" },
  { seq: 5, arrive: "13:15", depart: "13:45", patient: "Sandra Cole",       address: "230 Oakridge Ln, Apopka FL",      visit: "DFU dressing change",                 windowOk: true,  drive: "26 min",   status: "scheduled" },
  { seq: 6, arrive: "14:25", depart: "14:55", patient: "Carlos Reyes",      address: "76 South Bumby, Orlando FL",      visit: "VLU follow-up",                       windowOk: true,  drive: "16 min",   status: "scheduled" },
  { seq: 7, arrive: "15:30", depart: "16:00", patient: "Linda Hayes",       address: "1145 W Colonial, Orlando FL",     visit: "Arterial reassessment + photo",       windowOk: true,  drive: "12 min",   status: "delay"    },
  { seq: 8, arrive: "16:35", depart: "17:00", patient: "Helen Park",        address: "2104 Curry Ford Rd, Orlando FL",  visit: "Heel offloading review",              windowOk: true,  drive: "18 min",   status: "scheduled" },
];

export default async function RoutesPage() {
  const session = await getSession();
  return (
    <AppShell
      title="Route Planner"
      subtitle="Home visits, mileage, and capture readiness — optimised."
      user={{ name: "Dr. Rachel Morgan", role: session?.role ?? "clinician" }}
    >
      <section className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <KpiTile label="Stops today" value="8" delta="6 home · 2 clinic" />
        <KpiTile label="Distance" value="42.6 mi" delta="−18% vs unoptimised" tone="success" />
        <KpiTile label="Drive time" value="2h 15m" delta="ends 17:00" />
        <KpiTile label="Window adherence" value="78%" delta="1 tight window" tone="warn" />
        <KpiTile label="Efficiency" value="94%" delta="vs 86% avg" tone="success" />
        <KpiTile label="Supplies loaded" value="100%" delta="checklist complete" tone="success" />
      </section>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-[1fr_360px]">
        <div className="card overflow-hidden">
          <div className="flex items-center justify-between border-b border-hairline bg-surface-2 px-4 py-3 text-xs">
            <div className="flex gap-1.5">
              <Chip active>Today</Chip>
              <Chip>This week</Chip>
              <Chip>Upcoming</Chip>
            </div>
            <button className="btn btn-primary">Optimize Route</button>
          </div>

          <div className="grid grid-cols-1 gap-0 lg:grid-cols-2">
            <ol className="divide-y divide-hairline">
              {STOPS.map((s) => (
                <li
                  key={s.seq}
                  className={`flex gap-3 p-4 ${s.status === "next" ? "bg-accent/5" : ""}`}
                >
                  <div className="flex flex-col items-center">
                    <span
                      className={`grid h-7 w-7 place-items-center rounded-full font-mono text-xs font-semibold ${
                        s.status === "complete"
                          ? "bg-success/15 text-success"
                          : s.status === "delay"
                            ? "bg-warn/15 text-warn"
                            : s.status === "next"
                              ? "bg-accent text-white dark:text-ink"
                              : "border border-hairline text-ink-soft"
                      }`}
                    >
                      {s.seq}
                    </span>
                    <span className="mt-1 h-full w-px bg-hairline" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline justify-between gap-2">
                      <p className="truncate font-medium text-ink">{s.patient}</p>
                      <span className="font-mono text-[11px] text-ink-muted">
                        {s.arrive}–{s.depart}
                      </span>
                    </div>
                    <p className="truncate text-xs text-ink-muted">{s.address}</p>
                    <p className="mt-1 text-xs text-ink-soft">{s.visit}</p>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px]">
                      <span className="text-ink-muted">+{s.drive} drive</span>
                      <span className={`pill ${s.windowOk ? "pill-success" : "pill-warn"}`}>
                        {s.windowOk ? "in window" : "tight window"}
                      </span>
                      {s.status === "complete" && <span className="pill pill-success">Complete</span>}
                      {s.status === "next" && <span className="pill pill-accent">Up next</span>}
                      {s.status === "delay" && <span className="pill pill-warn">Traffic alert</span>}
                    </div>
                  </div>
                </li>
              ))}
            </ol>

            <MapStub stops={STOPS} />
          </div>
        </div>

        <aside className="space-y-4">
          <div className="card p-4">
            <span className="eyebrow">Route summary</span>
            <ul className="mt-2 space-y-1.5 text-xs">
              <Row label="Stops" value="8" />
              <Row label="Distance" value="42.6 mi" />
              <Row label="Drive time" value="2h 15m" />
              <Row label="Visit time" value="3h 50m" />
              <Row label="Day end" value="17:00" />
              <Row label="Efficiency" value="94%" tone="success" />
            </ul>
          </div>

          <div className="card p-4">
            <span className="eyebrow">Pre-departure checklist</span>
            <ul className="mt-2 space-y-1.5 text-xs">
              <Check label="ActiGraft+ 4×4 (Patricia, James)" />
              <Check label="Compression wraps (3) — Robert" />
              <Check label="Debridement kit + photo + biopsy media" />
              <Check label="iOS app capture queue cleared" />
              <Check label="Cooler ice packs + temp logger" />
              <Check label="Hand hygiene + PPE kit" warn />
            </ul>
          </div>

          <div className="card p-4">
            <span className="eyebrow">Today&apos;s supplies overview</span>
            <ul className="mt-2 space-y-1 text-xs text-ink-soft">
              <li className="flex justify-between"><span>Total items packed</span><span className="font-mono text-ink">26</span></li>
              <li className="flex justify-between"><span>Cold-chain items</span><span className="font-mono text-ink">3</span></li>
              <li className="flex justify-between"><span>UDI to log on visit</span><span className="font-mono text-ink">2</span></li>
            </ul>
            <button className="btn btn-secondary mt-3 w-full justify-center">View all checklists</button>
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

function Row({ label, value, tone }: { label: string; value: string; tone?: "success" }) {
  return (
    <li className="flex justify-between">
      <span className="text-ink-muted">{label}</span>
      <span className={`tabular-nums ${tone === "success" ? "text-success" : "text-ink"}`}>{value}</span>
    </li>
  );
}

function Check({ label, warn }: { label: string; warn?: boolean }) {
  return (
    <li className="flex items-start gap-2">
      <span
        className={`mt-0.5 grid h-3 w-3 place-items-center rounded-sm ${
          warn ? "bg-warn/20 text-warn" : "bg-success/20 text-success"
        }`}
      >
        <span className="text-[10px]">✓</span>
      </span>
      <span className={`flex-1 ${warn ? "text-warn" : "text-ink-soft"}`}>{label}</span>
    </li>
  );
}

/**
 * Stylised SVG map: shows the route between stops without a real
 * tile-server dependency. Coordinates are made up — not load-bearing.
 */
function MapStub({ stops }: { stops: Stop[] }) {
  const points: ReadonlyArray<readonly [number, number]> = [
    [40, 250], [110, 200], [180, 230], [240, 160], [310, 140], [380, 190],
    [450, 150], [510, 220], [560, 280],
  ];
  const path = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p[0]} ${p[1]}`)
    .join(" ");
  return (
    <div
      className="relative h-[520px] border-l border-hairline"
      style={{
        background:
          "radial-gradient(ellipse at 30% 30%, rgba(34,211,238,0.10), transparent 60%), radial-gradient(ellipse at 70% 80%, rgba(212,169,74,0.06), transparent 60%), #0a1428",
      }}
    >
      <div
        className="absolute inset-0 opacity-25"
        style={{
          backgroundImage:
            "linear-gradient(rgba(34,211,238,0.18) 1px, transparent 1px), linear-gradient(90deg, rgba(34,211,238,0.18) 1px, transparent 1px)",
          backgroundSize: "32px 32px",
        }}
      />
      <svg viewBox="0 0 600 520" className="absolute inset-0 h-full w-full">
        <path d={path} fill="none" stroke="rgb(var(--accent))" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" strokeDasharray="6 6" />
        {points.map((p, i) => {
          const s = stops[i];
          const tone =
            s?.status === "complete" ? "rgb(var(--success))" :
            s?.status === "next" ? "rgb(var(--accent))" :
            s?.status === "delay" ? "rgb(var(--warn))" : "rgb(var(--ink-muted))";
          return (
            <g key={i}>
              <circle cx={p[0]} cy={p[1]} r="11" fill="rgb(0 0 0 / 0.5)" />
              <circle cx={p[0]} cy={p[1]} r="9" fill={tone} />
              <text
                x={p[0]}
                y={p[1] + 3.5}
                textAnchor="middle"
                fontFamily="monospace"
                fontSize="10"
                fontWeight="700"
                fill="white"
              >
                {i + 1}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="absolute left-3 top-3 rounded border border-cyan-300/30 bg-cyan-300/10 px-2 py-1 text-[10px] uppercase tracking-[0.16em] text-cyan-100/80">
        Orlando · 42.6 mi · 2h 15m
      </div>
      <div className="absolute right-3 top-3 flex gap-2 text-[10px]">
        <span className="rounded border border-warn/40 bg-warn/10 px-2 py-1 text-warn">Traffic alert</span>
        <span className="rounded border border-success/40 bg-success/10 px-2 py-1 text-success">Optimal route</span>
      </div>
    </div>
  );
}
