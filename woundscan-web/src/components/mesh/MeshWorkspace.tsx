"use client";

import { useState } from "react";
import { fmtDateTime } from "@/lib/format";
import { MeshCanvas } from "@/components/mesh/MeshCanvas";
import { DepthSparkline } from "@/components/mesh/DepthSparkline";

type LatestSummary = {
  capturedAt: string;
  volumeCm3: number;
  surfaceAreaCm2: number;
  maxDepthCm: number;
  meanDepthCm: number;
  perimeterCm: number;
  qualityGrade: string;
};

type Props = {
  measurementId: string | null;
  latest: LatestSummary | null;
  depthSeries: number[];
};

type RenderMode = "realistic" | "wireframe" | "tissue";
type Tab = "view3d" | "analytics";

const DISPLAY_LAYERS = [
  { key: "mesh", label: "3D Mesh", default: true },
  { key: "depthMap", label: "Depth Map", default: true },
  { key: "heatMap", label: "Heat Map", default: false },
  { key: "tissueLayers", label: "Tissue Layers", default: true },
  { key: "measurements", label: "Measurements", default: false },
] as const;

type LayerKey = (typeof DISPLAY_LAYERS)[number]["key"];

export function MeshWorkspace({ measurementId, latest, depthSeries }: Props) {
  const [tab, setTab] = useState<Tab>("view3d");
  const [renderMode, setRenderMode] = useState<RenderMode>("realistic");
  const [layers, setLayers] = useState<Record<LayerKey, boolean>>(() =>
    Object.fromEntries(DISPLAY_LAYERS.map((l) => [l.key, l.default])) as Record<LayerKey, boolean>,
  );

  const meshUrl = measurementId
    ? `/api/proxy/measurements/${measurementId}/mesh`
    : null;
  const [autoRotate, setAutoRotate] = useState(false);
  const [crossSection, setCrossSection] = useState(false);
  const [fitVersion, setFitVersion] = useState(0);
  const [layersOpen, setLayersOpen] = useState(false);

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[280px_1fr_300px]">
      {/* ─── Left panel ─── */}
      <aside className="card flex flex-col gap-5 p-4">
        <div className="flex items-center justify-between">
          <span className="font-display text-xs font-semibold uppercase tracking-[0.18em] text-accent">
            Wound parameters
          </span>
          <button
            type="button"
            className="text-[11px] text-ink-muted hover:text-ink"
            title="Run a new simulation pass"
          >
            + New simulation
          </button>
        </div>

        <ParamGroup>
          <Param label="Length" value={latest ? `${(latest.surfaceAreaCm2 ** 0.5 * 1.4).toFixed(2)} cm` : "—"} />
          <Param label="Width" value={latest ? `${(latest.surfaceAreaCm2 ** 0.5 * 0.95).toFixed(2)} cm` : "—"} />
          <Param label="Depth" value={latest ? `${latest.maxDepthCm.toFixed(2)} cm` : "—"} />
          <Param label="Surface area" value={latest ? `${latest.surfaceAreaCm2.toFixed(2)} cm²` : "—"} />
          <Param label="Volume" value={latest ? `${latest.volumeCm3.toFixed(2)} cm³` : "—"} />
        </ParamGroup>

        <Divider />

        <div>
          <span className="label">Wound type</span>
          <select className="input" defaultValue="dfu">
            <option value="dfu">Diabetic Ulcer</option>
            <option value="vlu">Venous Leg Ulcer</option>
            <option value="pressure">Pressure Injury</option>
            <option value="surgical">Surgical Dehiscence</option>
          </select>
        </div>

        <div>
          <span className="label flex items-center justify-between">
            <span>Tissue composition</span>
          </span>
          <TissueBar />
          <ul className="mt-2 space-y-1 text-[11px]">
            <Legend color="rgb(245 158 11)" label="Granulation" pct={62} />
            <Legend color="rgb(239 68 68)" label="Slough" pct={28} />
            <Legend color="rgb(120 113 108)" label="Eschar" pct={10} />
          </ul>
        </div>

        <button type="button" className="btn btn-primary mt-auto w-full justify-center">
          + Add Layer
        </button>
      </aside>

      {/* ─── Center: mesh canvas ─── */}
      <section className="card relative overflow-hidden p-0">
        <div className="absolute left-1/2 top-6 z-10 -translate-x-1/2 text-center">
          <div className="font-display text-2xl font-bold tracking-tight text-ink">
            Wound<span className="text-accent">Scan</span>
          </div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-ink-muted">
            powered by Albacete MedDev
          </div>
        </div>

        <div className="absolute right-4 top-4 z-10 flex rounded-md border border-hairline bg-surface/80 p-0.5 text-xs backdrop-blur">
          {(["view3d", "analytics"] as const).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className={`rounded px-3 py-1 font-medium transition ${
                tab === t ? "bg-accent text-white dark:text-ink" : "text-ink-soft hover:text-ink"
              }`}
            >
              {t === "view3d" ? "3D View" : "Analytics"}
            </button>
          ))}
        </div>

        <MeshCanvas
          meshUrl={meshUrl}
          mode={renderMode}
          layers={layers}
          analytics={tab === "analytics"}
          autoRotate={autoRotate}
          fitVersion={fitVersion}
          crossSection={crossSection}
        />

        {/* Action bar */}
        <div className="absolute inset-x-0 bottom-0 z-10 border-t border-hairline bg-surface/85 px-4 py-3 backdrop-blur">
          <div className="flex items-center justify-between gap-3">
            <div className="relative flex items-center gap-2">
              <ToolButton
                label={autoRotate ? "Stop rotation" : "Auto-rotate"}
                icon={<RotateIcon />}
                active={autoRotate}
                onClick={() => setAutoRotate((v) => !v)}
              />
              <ToolButton
                label="Fit to view"
                icon={<ZoomIcon />}
                onClick={() => setFitVersion((v) => v + 1)}
              />
              <ToolButton
                label="Display layers"
                icon={<LayersIcon />}
                active={layersOpen}
                onClick={() => setLayersOpen((v) => !v)}
              />
              <ToolButton
                label={crossSection ? "Hide cross-section" : "Show cross-section"}
                icon={<CrossSectionIcon />}
                active={crossSection}
                onClick={() => setCrossSection((v) => !v)}
              />
              {layersOpen && (
                <div
                  className="absolute bottom-12 left-0 z-30 w-56 rounded-md border border-hairline bg-surface p-2 shadow-elevated"
                  role="menu"
                >
                  {DISPLAY_LAYERS.map((l) => (
                    <label
                      key={l.key}
                      className="flex cursor-pointer items-center justify-between rounded px-2 py-1.5 text-xs text-ink-soft hover:bg-surface-2"
                    >
                      <span>{l.label}</span>
                      <input
                        type="checkbox"
                        checked={layers[l.key]}
                        onChange={(e) =>
                          setLayers((s) => ({ ...s, [l.key]: e.target.checked }))
                        }
                        className="rounded border-hairline text-accent focus:ring-accent"
                      />
                    </label>
                  ))}
                </div>
              )}
            </div>
            {measurementId ? (
              <a
                href={`/api/proxy/measurements/${measurementId}/pdf`}
                target="_blank"
                rel="noreferrer"
                className="btn btn-primary"
              >
                Generate Report
              </a>
            ) : (
              <button type="button" className="btn btn-primary" disabled>
                Generate Report
              </button>
            )}
          </div>
        </div>
      </section>

      {/* ─── Right panel ─── */}
      <aside className="card flex flex-col gap-5 p-4">
        <div>
          <span className="label">Render mode</span>
          <select
            className="input"
            value={renderMode}
            onChange={(e) => setRenderMode(e.target.value as RenderMode)}
          >
            <option value="realistic">Realistic</option>
            <option value="wireframe">Wireframe</option>
            <option value="tissue">Tissue depth</option>
          </select>
        </div>

        <div>
          <span className="label">Display</span>
          <div className="space-y-1.5">
            {DISPLAY_LAYERS.map((l) => (
              <label
                key={l.key}
                className="flex cursor-pointer items-center justify-between rounded-md border border-hairline bg-surface px-3 py-2 text-sm text-ink-soft transition hover:border-accent/50 hover:text-ink"
              >
                <span>{l.label}</span>
                <input
                  type="checkbox"
                  className="rounded border-hairline text-accent focus:ring-accent"
                  checked={layers[l.key]}
                  onChange={(e) => setLayers((s) => ({ ...s, [l.key]: e.target.checked }))}
                />
              </label>
            ))}
          </div>
        </div>

        <div>
          <span className="label">Depth profile</span>
          <div className="card p-3">
            <DepthSparkline series={depthSeries} />
            <div className="mt-2 flex items-center justify-between text-[11px] text-ink-muted">
              <span>{depthSeries.length || 0} captures</span>
              {latest && <span>now {latest.maxDepthCm.toFixed(2)} cm</span>}
            </div>
          </div>
        </div>

        <a
          href={meshUrl ?? "#"}
          target="_blank"
          rel="noreferrer"
          download={measurementId ? `wound_${measurementId}.obj` : undefined}
          aria-disabled={!meshUrl}
          className={`btn btn-secondary w-full justify-center ${meshUrl ? "" : "pointer-events-none opacity-50"}`}
        >
          Export OBJ
        </a>

        {latest && (
          <div className="mt-auto rounded-md border border-hairline bg-surface-2 p-3 text-[11px] text-ink-muted">
            <div className="flex items-center justify-between">
              <span>Captured</span>
              <span className="text-ink-soft">{fmtDateTime(latest.capturedAt)}</span>
            </div>
            <div className="mt-1 flex items-center justify-between">
              <span>Quality</span>
              <span className="text-ink-soft">grade {latest.qualityGrade}</span>
            </div>
          </div>
        )}
      </aside>

      <p className="lg:col-span-3 text-center text-[11px] text-ink-muted">
        WoundScan v1.0.0 · Albacete MedDev · all rights reserved.
      </p>
    </div>
  );
}

function ParamGroup({ children }: { children: React.ReactNode }) {
  return <ul className="space-y-2 text-sm">{children}</ul>;
}

function Param({ label, value }: { label: string; value: string }) {
  return (
    <li className="flex items-center justify-between">
      <span className="text-ink-muted">{label}</span>
      <span className="font-display font-semibold tabular-nums text-ink">{value}</span>
    </li>
  );
}

function Divider() {
  return <hr className="border-hairline" />;
}

function TissueBar() {
  return (
    <div className="flex h-2 overflow-hidden rounded-full bg-hairline">
      <span style={{ width: "62%", background: "rgb(245 158 11)" }} />
      <span style={{ width: "28%", background: "rgb(239 68 68)" }} />
      <span style={{ width: "10%", background: "rgb(120 113 108)" }} />
    </div>
  );
}

function Legend({ color, label, pct }: { color: string; label: string; pct: number }) {
  return (
    <li className="flex items-center justify-between text-ink-soft">
      <span className="flex items-center gap-2">
        <span className="inline-block h-2 w-2 rounded-full" style={{ background: color }} />
        {label}
      </span>
      <span className="tabular-nums text-ink-muted">{pct}%</span>
    </li>
  );
}

function ToolButton({
  label,
  icon,
  active = false,
  onClick,
}: {
  label: string;
  icon: React.ReactNode;
  active?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      aria-pressed={active}
      onClick={onClick}
      className={`grid h-9 w-9 place-items-center rounded-md border transition ${
        active
          ? "border-accent bg-accent/15 text-accent"
          : "border-hairline bg-surface text-ink-soft hover:border-accent hover:text-accent"
      }`}
    >
      {icon}
    </button>
  );
}

function RotateIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12a9 9 0 1 1-3-6.7" />
      <path d="M21 4v5h-5" />
    </svg>
  );
}
function ZoomIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="7" />
      <path d="M21 21l-4.3-4.3M8 11h6M11 8v6" />
    </svg>
  );
}
function LayersIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3l9 5-9 5-9-5 9-5z" />
      <path d="M3 13l9 5 9-5" />
      <path d="M3 18l9 5 9-5" />
    </svg>
  );
}
function CrossSectionIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M3 12h18M12 3v18" />
    </svg>
  );
}
