import Link from "next/link";
import { AppShell } from "@/components/portal/AppShell";
import { getSession } from "@/lib/auth";
import { MeshWorkspace } from "@/components/mesh/MeshWorkspace";
import {
  ProgressionResponseSchema,
  type ProgressionResponse,
} from "@/lib/api";
import { mockProgression } from "@/lib/sample";

const API_BASE = process.env.API_URL ?? "http://localhost:8000";

async function fetchProgression(
  woundId: string,
  token: string,
): Promise<ProgressionResponse | null> {
  try {
    const res = await fetch(`${API_BASE}/wounds/${woundId}/progression`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return ProgressionResponseSchema.parse(await res.json());
  } catch {
    return null;
  }
}

export default async function MeshPage({ params }: { params: { id: string } }) {
  const session = await getSession();
  const real = await fetchProgression(params.id, session?.token ?? "");
  // Demo fallback so the workspace always has stats + a depth series even
  // when the engine API isn't reachable.
  const progression = real ?? mockProgression(params.id);
  const points = progression.points;
  const latest = points[0];

  return (
    <AppShell
      title="3D Wound Analysis"
      subtitle="High-resolution 3D reconstruction and quantitative analysis"
      user={{ name: "Dr. Rachel Morgan", role: session?.role ?? "clinician" }}
    >
      <nav className="mb-4 text-sm text-ink-muted">
        <Link href="/wounds" className="hover:text-ink">3D Wound Analysis</Link>
        <span className="mx-2 text-ink-muted/60">/</span>
        <Link href={`/wounds/${params.id}`} className="hover:text-ink">{params.id.slice(0, 8)}</Link>
        <span className="mx-2 text-ink-muted/60">/</span>
        <span className="text-ink-soft">3D Mesh</span>
      </nav>

      <MeshWorkspace
        measurementId={latest?.measurement_id ?? null}
        latest={
          latest
            ? {
                capturedAt: latest.captured_at,
                volumeCm3: latest.volume_cm3,
                surfaceAreaCm2: latest.surface_area_cm2,
                maxDepthCm: latest.max_depth_cm,
                meanDepthCm: latest.mean_depth_cm,
                perimeterCm: latest.perimeter_cm,
                qualityGrade: latest.quality_grade,
              }
            : null
        }
        depthSeries={points.slice(0, 12).reverse().map((p) => p.max_depth_cm)}
      />
    </AppShell>
  );
}
