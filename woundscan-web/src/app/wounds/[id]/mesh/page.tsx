import Link from "next/link";
import { Header } from "@/components/Header";
import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";
import { MeshWorkspace } from "@/components/mesh/MeshWorkspace";
import {
  ProgressionResponseSchema,
  type ProgressionResponse,
} from "@/lib/api";

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
  if (!session) redirect("/login");

  const progression = await fetchProgression(params.id, session.token);
  const points = progression?.points ?? [];
  const latest = points[0];

  return (
    <>
      <Header />
      <main className="mx-auto max-w-[1480px] px-6 py-6">
        <nav className="mb-4 text-sm text-ink-muted">
          <Link href="/wounds" className="hover:text-ink">
            Wounds
          </Link>
          <span className="mx-2 text-ink-muted/60">/</span>
          <Link href={`/wounds/${params.id}`} className="hover:text-ink">
            {params.id.slice(0, 8)}
          </Link>
          <span className="mx-2 text-ink-muted/60">/</span>
          <span className="text-ink-soft">3D Mesh</span>
        </nav>

        <MeshWorkspace
          woundId={params.id}
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
          depthSeries={points
            .slice(0, 12)
            .reverse()
            .map((p) => p.max_depth_cm)}
        />
      </main>
    </>
  );
}
