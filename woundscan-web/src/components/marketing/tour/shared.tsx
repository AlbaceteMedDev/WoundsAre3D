import type { Patient } from "@/lib/sample";

/** Views available inside the simulated portal window. */
export type TourView =
  | "dashboard"
  | "patients"
  | "wound"
  | "scan"
  | "notes"
  | "inventory"
  | "claims"
  | "reports"
  | "routes"
  | "admin";

export type TourNavigate = (view: TourView, patientId?: string) => void;

export function ViewHeader({
  title,
  sub,
  right,
}: {
  title: string;
  sub: string;
  right?: React.ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-2">
      <div>
        <h3 className="font-display text-lg font-semibold text-ink">{title}</h3>
        <p className="text-xs text-ink-muted">{sub}</p>
      </div>
      {right}
    </header>
  );
}

export function MiniMetric({ k, v }: { k: string; v: string }) {
  return (
    <li className="rounded border border-hairline bg-surface-2 px-1.5 py-1">
      <div className="text-[9px] uppercase tracking-wider text-ink-muted">{k}</div>
      <div className="font-display text-[11px] font-semibold text-ink">{v}</div>
    </li>
  );
}

export function Chip({
  active,
  onClick,
  children,
}: {
  active?: boolean;
  onClick?: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`inline-flex items-center rounded-full px-3 py-1 text-[11px] font-medium transition ${
        active
          ? "bg-accent text-white dark:text-ink"
          : "border border-hairline text-ink-soft hover:border-accent hover:text-accent"
      }`}
    >
      {children}
    </button>
  );
}

/* ── Deterministic per-patient measurement history ─────────────────── */

export type Visit = {
  visit: string;
  date: string;
  area: number;
  depth: number;
  grade: "A" | "B";
};

function hashStr(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h;
}

/**
 * Builds a consistent 6-visit history for a patient: initial size seeded
 * from the patient id, trend driven by their healingPct — so every chart
 * in the demo tells the same story for the same patient.
 */
export function visitsFor(p: Patient): Visit[] {
  const h = hashStr(p.id);
  const initialArea = 14 + (h % 90) / 10; // 14–23 cm²
  const initialDepth = 10 + ((h >> 8) % 70) / 10; // 10–17 mm
  const remaining = 1 - p.healingPct / 100; // fraction of wound left at V6
  const dates = ["2026-03-25", "2026-04-01", "2026-04-08", "2026-04-15", "2026-04-22", "2026-04-29"];
  return dates
    .map((date, i) => {
      const t = i / (dates.length - 1); // 0 = first visit, 1 = latest
      const scale = 1 - t * (1 - remaining);
      const wobble = 1 + ((((h >> (i * 4)) % 9) - 4) / 100); // ±4%
      return {
        visit: `V${i + 1}`,
        date,
        area: +(initialArea * scale * wobble).toFixed(1),
        depth: +(initialDepth * Math.pow(scale, 0.7) * wobble).toFixed(1),
        grade: (((h >> (i * 2)) & 3) === 0 ? "B" : "A") as "A" | "B",
      };
    })
    .reverse(); // latest first, engine convention
}
