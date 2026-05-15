import Link from "next/link";
import { MeshWorkspace } from "@/components/mesh/MeshWorkspace";

/**
 * Public demo route for the 3D wound mesh viewer.
 *
 * Renders the same MeshWorkspace component used inside the portal, but
 * sources its mesh from the static `/demo-wound.obj` asset so the viewer
 * is visible without an authenticated session or a running engine API.
 *
 * Use this for screenshots, design reviews, and stakeholder demos.
 */
export default function MeshDemoPage() {
  return (
    <main className="min-h-screen bg-bg px-4 py-6 md:px-6 md:py-8">
      <header className="mx-auto mb-6 max-w-7xl">
        <nav className="mb-3 text-sm text-ink-muted">
          <Link href="/" className="hover:text-ink">WoundScan</Link>
          <span className="mx-2 text-ink-muted/60">/</span>
          <span className="text-ink-soft">3D Mesh Viewer Demo</span>
        </nav>
        <h1 className="font-display text-2xl font-semibold text-ink md:text-3xl">
          3D Wound Mesh Viewer
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-ink-muted">
          Public demo. The mesh below is synthetic (Gaussian wound bed,
          ~40 mm × 40 mm × 12 mm deep). The same component renders real
          patient meshes inside the authenticated portal at{" "}
          <code className="text-ink-soft">/wounds/[id]/mesh</code>.
        </p>
      </header>

      <div className="mx-auto max-w-7xl">
        <MeshWorkspace
          measurementId="demo"
          meshUrlOverride="/demo-wound.obj"
          latest={{
            capturedAt: new Date().toISOString(),
            volumeCm3: 4.32,
            surfaceAreaCm2: 11.2,
            maxDepthCm: 1.2,
            meanDepthCm: 0.54,
            perimeterCm: 12.8,
            qualityGrade: "A",
          }}
          depthSeries={[1.8, 1.65, 1.5, 1.42, 1.35, 1.3, 1.25, 1.22, 1.2]}
        />
      </div>
    </main>
  );
}
