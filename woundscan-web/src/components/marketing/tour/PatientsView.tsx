"use client";

import { useMemo, useState } from "react";
import { PATIENTS } from "@/lib/sample";
import { Chip, ViewHeader, type TourNavigate } from "./shared";

const FILTERS = ["all", "active", "high-risk", "remission", "discharged"] as const;

/** Searchable, filterable roster — clicking a row opens that patient's chart. */
export function PatientsView({ go }: { go: TourNavigate }) {
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("all");

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return PATIENTS.filter(
      (p) =>
        (filter === "all" || p.status === filter) &&
        (!needle ||
          p.name.toLowerCase().includes(needle) ||
          p.mrn.toLowerCase().includes(needle) ||
          p.primaryDx.toLowerCase().includes(needle)),
    );
  }, [q, filter]);

  return (
    <div className="space-y-4">
      <ViewHeader
        title="Patients"
        sub={`${rows.length} of ${PATIENTS.length} shown · search and filters are live`}
        right={
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search name, MRN, dx…"
            className="input !w-52"
            aria-label="Search patients"
          />
        }
      />

      <div className="flex flex-wrap gap-1.5">
        {FILTERS.map((f) => (
          <Chip key={f} active={filter === f} onClick={() => setFilter(f)}>
            {f === "all" ? `All (${PATIENTS.length})` : `${f} (${PATIENTS.filter((p) => p.status === f).length})`}
          </Chip>
        ))}
      </div>

      <div className="card overflow-x-auto !p-0">
        <table className="table-base">
          <thead>
            <tr>
              <th>Patient</th>
              <th>Primary dx</th>
              <th>Clinician</th>
              <th>Status</th>
              <th>Healing</th>
              <th>Last seen</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <tr
                key={p.id}
                onClick={() => go("wound", p.id)}
                className="cursor-pointer hover:bg-surface-2"
                title={`Open ${p.name}'s wound record`}
              >
                <td>
                  <div className="font-medium text-ink">{p.name}</div>
                  <div className="font-mono text-[10px] text-ink-muted">{p.mrn} · {p.age}{p.sex}</div>
                </td>
                <td className="max-w-[180px] truncate text-ink-soft">{p.primaryDx}</td>
                <td className="whitespace-nowrap text-ink-muted">{p.clinician}</td>
                <td>
                  <span
                    className={`pill ${
                      p.status === "high-risk"
                        ? "pill-danger"
                        : p.status === "remission"
                          ? "pill-success"
                          : p.status === "discharged"
                            ? "pill-neutral"
                            : "pill-accent"
                    }`}
                  >
                    {p.status}
                  </span>
                </td>
                <td className="min-w-[110px]">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-hairline">
                      <span
                        className={`block h-full ${p.healingPct >= 60 ? "bg-success" : p.healingPct >= 30 ? "bg-accent" : "bg-warn"}`}
                        style={{ width: `${p.healingPct}%` }}
                      />
                    </div>
                    <span className="tabular-nums text-[11px] text-ink-muted">{p.healingPct}%</span>
                  </div>
                </td>
                <td className="whitespace-nowrap text-ink-muted">{p.lastSeen}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="py-6 text-center text-ink-muted">
                  No patients match — clear the search or filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="text-center text-[11px] text-ink-muted">
        Click any row to open that patient&rsquo;s wound record — each chart is unique to the patient.
      </p>
    </div>
  );
}
