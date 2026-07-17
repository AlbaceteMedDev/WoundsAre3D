"use client";

import { useState } from "react";
import { KpiTile } from "@/components/portal/KpiTile";
import { ViewHeader } from "./shared";

type StopStatus = "complete" | "next" | "scheduled" | "delay";

type Stop = {
  seq: number;
  arrive: string;
  patient: string;
  address: string;
  visit: string;
  status: StopStatus;
  /** Position on the SVG map, 0–100 coordinate space. */
  x: number;
  y: number;
};

const INITIAL: Stop[] = [
  { seq: 1, arrive: "08:30", patient: "Patricia Johnson", address: "742 Park Ave, Orlando", visit: "Wound check + ActiGraft+ q14d", status: "complete", x: 16, y: 68 },
  { seq: 2, arrive: "09:25", patient: "James Carter", address: "1208 Grand St, Winter Park", visit: "Surgical follow-up", status: "complete", x: 30, y: 40 },
  { seq: 3, arrive: "10:20", patient: "Robert Williams", address: "514 Edgewater Dr, Orlando", visit: "VLU compression check", status: "next", x: 46, y: 58 },
  { seq: 4, arrive: "11:30", patient: "Margaret Chen", address: "918 Lakeview Pkwy, Maitland", visit: "Sacral PI · debridement", status: "scheduled", x: 58, y: 26 },
  { seq: 5, arrive: "13:15", patient: "Sandra Cole", address: "230 Oakridge Ln, Apopka", visit: "DFU dressing change", status: "scheduled", x: 72, y: 48 },
  { seq: 6, arrive: "14:25", patient: "Carlos Reyes", address: "76 South Bumby, Orlando", visit: "VLU follow-up", status: "scheduled", x: 66, y: 74 },
  { seq: 7, arrive: "15:30", patient: "Linda Hayes", address: "1145 W Colonial, Orlando", visit: "Arterial reassessment", status: "delay", x: 82, y: 62 },
  { seq: 8, arrive: "16:35", patient: "Helen Park", address: "2104 Curry Ford Rd, Orlando", visit: "Heel offloading review", status: "scheduled", x: 90, y: 34 },
];

/**
 * Route planner — click stops to focus them on the map, and complete the
 * "up next" visit to watch the day advance.
 */
export function RoutesView() {
  const [stops, setStops] = useState(INITIAL);
  const [focus, setFocus] = useState(3);

  const completeNext = () => {
    setStops((prev) => {
      const idx = prev.findIndex((s) => s.status === "next");
      if (idx === -1) return prev;
      const next = prev.map((s, i) => {
        if (i === idx) return { ...s, status: "complete" as StopStatus };
        return s;
      });
      const upcoming = next.findIndex((s) => s.status === "scheduled" || s.status === "delay");
      if (upcoming !== -1) next[upcoming] = { ...next[upcoming]!, status: "next" };
      return next;
    });
  };

  const done = stops.filter((s) => s.status === "complete").length;

  return (
    <div className="space-y-4">
      <ViewHeader
        title="Route Planner"
        sub="Home visits, mileage, capture readiness — complete the next stop and watch the day advance"
        right={
          <button
            type="button"
            onClick={completeNext}
            disabled={done === stops.length}
            className="btn btn-primary text-xs disabled:opacity-50"
          >
            {done === stops.length ? "Day complete ✓" : "Arrive & complete next stop"}
          </button>
        }
      />

      <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-4">
        <KpiTile label="Stops today" value={`${done} / ${stops.length}`} delta="6 home · 2 clinic" tone="accent" />
        <KpiTile label="Distance" value="42.6 mi" delta="−18% vs unoptimised" tone="success" />
        <KpiTile label="Drive time" value="2h 15m" delta="ends 17:00" />
        <KpiTile label="Efficiency" value="94%" delta="vs 86% avg" tone="success" />
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        {/* Stop list */}
        <ol className="card max-h-[330px] divide-y divide-hairline overflow-y-auto !p-0">
          {stops.map((s, i) => (
            <li key={s.seq}>
              <button
                type="button"
                onClick={() => setFocus(i)}
                className={`flex w-full gap-3 p-3 text-left transition ${
                  i === focus ? "bg-accent/5" : "hover:bg-surface-2"
                }`}
              >
                <span
                  className={`grid h-6 w-6 shrink-0 place-items-center rounded-full font-mono text-[11px] font-semibold ${
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
                <span className="min-w-0 flex-1">
                  <span className="flex items-baseline justify-between gap-2">
                    <span className="truncate text-sm font-medium text-ink">{s.patient}</span>
                    <span className="font-mono text-[10px] text-ink-muted">{s.arrive}</span>
                  </span>
                  <span className="block truncate text-[11px] text-ink-muted">{s.address}</span>
                  <span className="mt-0.5 flex items-center gap-1.5">
                    <span className="truncate text-[11px] text-ink-soft">{s.visit}</span>
                    {s.status === "complete" && <span className="pill pill-success">✓</span>}
                    {s.status === "next" && <span className="pill pill-accent">up next</span>}
                    {s.status === "delay" && <span className="pill pill-warn">traffic</span>}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ol>

        {/* Map */}
        <div className="card overflow-hidden !p-0">
          <svg viewBox="0 0 100 88" className="h-full w-full" role="img" aria-label="Route map with numbered visit stops">
            <rect width="100" height="88" fill="rgb(var(--surface-2))" />
            {/* street grid */}
            {[14, 30, 46, 62, 78].map((y) => (
              <line key={`h${y}`} x1="0" x2="100" y1={y} y2={y} stroke="rgb(var(--hairline))" strokeWidth="0.5" />
            ))}
            {[12, 28, 44, 60, 76, 92].map((x) => (
              <line key={`v${x}`} x1={x} x2={x} y1="0" y2="88" stroke="rgb(var(--hairline))" strokeWidth="0.5" />
            ))}
            {/* route line */}
            <polyline
              points={stops.map((s) => `${s.x},${s.y}`).join(" ")}
              fill="none"
              stroke="rgb(var(--accent))"
              strokeWidth="0.9"
              strokeDasharray="2.4 1.6"
              strokeLinejoin="round"
              opacity="0.75"
            />
            {stops.map((s, i) => (
              <g key={s.seq} onClick={() => setFocus(i)} style={{ cursor: "pointer" }}>
                {i === focus && (
                  <circle cx={s.x} cy={s.y} r="5.4" fill="rgb(var(--accent) / 0.15)">
                    <animate attributeName="r" values="4.6;6;4.6" dur="2s" repeatCount="indefinite" />
                  </circle>
                )}
                <circle
                  cx={s.x}
                  cy={s.y}
                  r="3.4"
                  fill={
                    s.status === "complete"
                      ? "rgb(var(--success))"
                      : s.status === "next"
                        ? "rgb(var(--accent))"
                        : s.status === "delay"
                          ? "rgb(var(--warn))"
                          : "rgb(var(--surface))"
                  }
                  stroke="rgb(var(--ink-muted))"
                  strokeWidth="0.5"
                />
                <text x={s.x} y={s.y + 1.6} textAnchor="middle" fontSize="4" fontWeight="700" fill={s.status === "scheduled" ? "rgb(var(--ink))" : "#fff"}>
                  {s.seq}
                </text>
              </g>
            ))}
          </svg>
        </div>
      </div>

      <div className="card flex flex-wrap items-center justify-between gap-2 p-3 text-[11px] text-ink-soft">
        <span>
          Focused: <strong className="text-ink">{stops[focus]!.patient}</strong> · {stops[focus]!.visit}
        </span>
        <span className="text-ink-muted">Route summary: 42.6 mi · 2h 15m drive · 3h 50m visits · ends 17:00</span>
      </div>
    </div>
  );
}
