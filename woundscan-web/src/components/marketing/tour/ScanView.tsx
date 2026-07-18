"use client";

import dynamic from "next/dynamic";
import { ViewHeader } from "./shared";

// The genuine portal mesh workspace — the wound care software itself.
const MeshWorkspace = dynamic(
  () => import("@/components/mesh/MeshWorkspace").then((m) => m.MeshWorkspace),
  {
    ssr: false,
    loading: () => (
      <div className="grid h-[520px] w-full place-items-center rounded-lg border border-hairline bg-surface">
        <span className="font-mono text-xs text-ink-muted">loading 3D scan studio…</span>
      </div>
    ),
  },
);

/**
 * 3D Scan Studio tab — not a replica: this mounts the actual
 * MeshWorkspace component clinicians use, on the bundled synthetic mesh.
 */
export function ScanView() {
  return (
    <div className="space-y-3">
      <ViewHeader
        title="3D Scan Studio"
        sub="This is the real viewer component — orbit, switch render modes, toggle layers, cut a cross-section, open Analytics"
        right={<span className="pill pill-accent">live component · synthetic mesh</span>}
      />
      <MeshWorkspace
        measurementId="demo"
        meshUrlOverride="/demo-wound.obj"
        latest={{
          capturedAt: new Date().toISOString(),
          volumeCm3: 4.32,
          surfaceAreaCm2: 11.2,
          maxDepthCm: 1.18,
          meanDepthCm: 0.54,
          perimeterCm: 12.8,
          qualityGrade: "A",
        }}
        depthSeries={[1.8, 1.65, 1.5, 1.42, 1.35, 1.3, 1.25, 1.22, 1.18]}
      />
    </div>
  );
}
