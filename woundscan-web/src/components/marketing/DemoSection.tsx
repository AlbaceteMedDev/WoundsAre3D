"use client";

import dynamic from "next/dynamic";
import { Reveal } from "./Reveal";

// The real portal mesh workspace, fed by the bundled synthetic OBJ.
const MeshWorkspace = dynamic(
  () => import("@/components/mesh/MeshWorkspace").then((m) => m.MeshWorkspace),
  {
    ssr: false,
    loading: () => (
      <div className="grid h-[640px] w-full place-items-center rounded-lg border border-hairline bg-surface">
        <span className="font-mono text-xs text-ink-muted">loading 3D workspace…</span>
      </div>
    ),
  },
);

/**
 * Live demo: embeds the identical MeshWorkspace component clinicians use
 * inside the authenticated portal — not a video, not a mock-up.
 */
export function DemoSection() {
  return (
    <section id="demo" className="relative scroll-mt-20 border-y border-hairline bg-surface/40 py-20 md:py-28">
      <div className="mk-section">
        <Reveal>
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <span className="eyebrow">Live demo — try it</span>
              <h2 className="mk-h2 mt-3">This is the actual portal viewer.</h2>
              <p className="mk-lead">
                Not a video. The workspace below is the same component clinicians use in the
                authenticated portal, rendering the engine&rsquo;s synthetic demonstration mesh. Orbit,
                toggle depth and tissue layers, cut a cross-section, open the analytics tab.
              </p>
            </div>
            <span className="mk-chip">interactive · WebGL</span>
          </div>
        </Reveal>

        <Reveal delay={120}>
          <div className="mt-10 overflow-hidden rounded-xl border border-hairline shadow-elevated">
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
        </Reveal>

        <Reveal delay={200}>
          <p className="mt-4 text-center text-xs text-ink-muted">
            Synthetic demonstration mesh (~40 × 40 × 12 mm Gaussian wound bed) — no patient data.
            Inside the portal, this same workspace renders real captures with full measurement
            history.
          </p>
        </Reveal>
      </div>
    </section>
  );
}
