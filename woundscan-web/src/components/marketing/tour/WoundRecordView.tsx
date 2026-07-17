"use client";

import { useMemo, useState } from "react";
import { Sparkline } from "@/components/portal/Sparkline";
import { PATIENTS } from "@/lib/sample";
import { MiniMetric, ViewHeader, visitsFor, type TourNavigate } from "./shared";

/**
 * Patient chart — visit history is generated per patient, and clicking a
 * visit row retargets the capture panel to that measurement.
 */
export function WoundRecordView({ patientId, go }: { patientId: string; go: TourNavigate }) {
  const patient = PATIENTS.find((p) => p.id === patientId) ?? PATIENTS[0]!;
  const visits = useMemo(() => visitsFor(patient), [patient]);
  const [selected, setSelected] = useState(0); // index into visits (0 = latest)

  const v = visits[selected] ?? visits[0]!;
  const first = visits[visits.length - 1]!;
  const areaChange = ((visits[0]!.area - first.area) / first.area) * 100;

  return (
    <div className="space-y-4">
      <ViewHeader
        title={`${patient.name} · ${patient.mrn}`}
        sub={`${patient.primaryDx} · ${patient.clinician} · ${patient.location}`}
        right={
          <div className="flex gap-2">
            <button type="button" onClick={() => go("patients")} className="btn btn-ghost text-xs">
              ← Roster
            </button>
            <button type="button" onClick={() => go("scan")} className="btn btn-secondary text-xs">
              Open in 3D Scan Studio
            </button>
          </div>
        }
      />

      <div className="grid gap-3 lg:grid-cols-[240px_1fr]">
        {/* Capture panel — follows the selected visit */}
        <div className="card p-3">
          <span className="eyebrow">Capture · {v.visit}</span>
          <div
            className="mt-2 overflow-hidden rounded-md"
            style={{ background: "radial-gradient(ellipse at 50% 42%, #0a1428 0%, #03060d 78%)" }}
          >
            <svg viewBox="0 0 220 170" className="w-full" role="img" aria-label={`Stylized 3D wound capture for visit ${v.visit}`}>
              {/* Ring radii scale with the selected visit's area */}
              {(() => {
                const k = Math.sqrt(v.area / visits[visits.length - 1]!.area);
                return (
                  <>
                    <ellipse cx="110" cy="84" rx={72 * k} ry={52 * k} fill="#12233d" />
                    <ellipse cx="110" cy="84" rx={52 * k} ry={36 * k} fill="#1d3a5f" />
                    <ellipse cx="110" cy="84" rx={34 * k} ry={23 * k} fill="#2c5d8f" />
                    <ellipse cx="110" cy="84" rx={18 * k} ry={12 * k} fill="#3f83bd" />
                    <ellipse cx="110" cy="84" rx={72 * k} ry={52 * k} fill="none" stroke="#22d3ee" strokeWidth="1" strokeDasharray="4 4" opacity="0.7" />
                  </>
                );
              })()}
              <line x1="38" y1="150" x2="182" y2="150" stroke="#22d3ee" strokeWidth="1" />
              <text x="86" y="146" fontSize="8" fontFamily="monospace" fill="#7dd3fc">
                bed {v.area.toFixed(1)} cm²
              </text>
              <circle cx="110" cy="84" r="4" fill="none" stroke="#fbbf24" strokeWidth="1" />
              <text x="118" y="80" fontSize="8" fontFamily="monospace" fill="#fbbf24">
                D {v.depth.toFixed(1)}
              </text>
            </svg>
          </div>
          <ul className="mt-2 grid grid-cols-2 gap-1.5 text-center text-[10px]">
            <MiniMetric k="Bed area" v={`${v.area.toFixed(1)} cm²`} />
            <MiniMetric k="Max depth" v={`${v.depth.toFixed(1)} mm`} />
            <MiniMetric k="Captured" v={v.date.slice(5)} />
            <MiniMetric k="Quality" v={`Grade ${v.grade}`} />
          </ul>
        </div>

        {/* Trajectory + history */}
        <div className="space-y-3">
          <div className="card p-4">
            <div className="flex items-baseline justify-between">
              <span className="eyebrow">Healing trajectory · bed area</span>
              <span className={`text-[11px] ${areaChange < 0 ? "text-success" : "text-warn"}`}>
                {areaChange.toFixed(1)}% over {visits.length - 1} visits
              </span>
            </div>
            <Sparkline
              data={[...visits].reverse().map((x, i) => ({ x: i, label: x.visit, y: x.area }))}
              height={120}
            />
          </div>
          <div className="card overflow-x-auto !p-0">
            <table className="table-base">
              <thead>
                <tr>
                  <th>Visit</th>
                  <th>Date</th>
                  <th className="text-right">Bed area</th>
                  <th className="text-right">Max depth</th>
                  <th>Quality</th>
                </tr>
              </thead>
              <tbody>
                {visits.map((row, i) => (
                  <tr
                    key={row.visit}
                    onClick={() => setSelected(i)}
                    className={`cursor-pointer ${i === selected ? "bg-accent/5" : "hover:bg-surface-2"}`}
                    title="View this capture"
                  >
                    <td className="font-mono text-xs">
                      {row.visit}
                      {i === selected && <span className="ml-1.5 text-accent">◀</span>}
                    </td>
                    <td className="whitespace-nowrap text-ink-muted">{row.date}</td>
                    <td className="text-right tabular-nums">{row.area.toFixed(1)} cm²</td>
                    <td className="text-right tabular-nums">{row.depth.toFixed(1)} mm</td>
                    <td>
                      <span className={`pill ${row.grade === "A" ? "pill-success" : "pill-accent"}`}>{row.grade}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Documentation */}
      <div className="card p-4">
        <div className="flex items-center justify-between">
          <span className="eyebrow">Progression note · {v.visit}</span>
          <button type="button" onClick={() => go("notes")} className="pill pill-success transition hover:opacity-80">
            signed · {patient.clinician} · open in Notes →
          </button>
        </div>
        <p className="mt-2 text-xs leading-relaxed text-ink-soft">
          Wound bed area {v.area.toFixed(1)} cm², max depth {v.depth.toFixed(1)} mm from fitted
          reference plane. Measurements instrument-derived (3D LiDAR capture, quality {v.grade});
          methodology and algorithm versions attached to this note.
        </p>
        <p className="mt-2 font-mono text-[10px] text-ink-muted">
          provenance sha256:6b1f…9c2e · algo v1.0.0 · audit chain #4,182 ✓
        </p>
      </div>
    </div>
  );
}
