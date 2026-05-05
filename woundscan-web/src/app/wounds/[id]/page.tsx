import Link from "next/link";
import { Header } from "@/components/Header";
import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";
import { TrajectoryChart } from "@/components/TrajectoryChart";
import { GraftPanel } from "@/components/GraftPanel";
import { ReimbursementPanel } from "@/components/ReimbursementPanel";
import { TrendBadge } from "@/components/TrendBadge";
import { NotesPanel } from "@/components/NotesPanel";
import { fmtDateTime } from "@/lib/format";
import {
  GraftApplicationListSchema,
  NoteListSchema,
  ProgressionResponseSchema,
  type GraftApplication,
  type NoteOut,
  type ProgressionResponse,
} from "@/lib/api";

const API_BASE = process.env.API_URL ?? "http://localhost:8000";

async function fetchJson<T>(
  path: string,
  token: string,
  parse: (json: unknown) => T,
  fallback: T,
): Promise<T> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (!res.ok) return fallback;
    return parse(await res.json());
  } catch {
    return fallback;
  }
}

export default async function WoundDetailPage({ params }: { params: { id: string } }) {
  const session = await getSession();
  if (!session) redirect("/login");

  const [progression, grafts, notes] = await Promise.all([
    fetchJson<ProgressionResponse | null>(
      `/wounds/${params.id}/progression`,
      session.token,
      (j) => ProgressionResponseSchema.parse(j),
      null,
    ),
    fetchJson<GraftApplication[]>(
      `/grafts/applications?wound_id=${params.id}`,
      session.token,
      (j) => GraftApplicationListSchema.parse(j),
      [],
    ),
    fetchJson<NoteOut[]>(
      `/notes?wound_id=${params.id}`,
      session.token,
      (j) => NoteListSchema.parse(j),
      [],
    ),
  ]);

  const points = progression?.points ?? [];
  const series = points.map((p) => ({
    date: p.captured_at.slice(0, 10),
    volume: p.volume_cm3,
    surfaceArea: p.surface_area_cm2,
    maxDepth: p.max_depth_cm,
  }));
  const latest = points[0];
  const latestGraft = grafts[0];

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl px-6 py-8">
        <nav className="mb-4 text-sm text-ink-muted">
          <Link href="/wounds" className="hover:text-ink">
            Wounds
          </Link>
          <span className="mx-2 text-ink-muted/60">/</span>
          <span className="text-ink-soft">{params.id.slice(0, 8)}</span>
        </nav>

        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <span className="eyebrow">Wound case</span>
            <h1 className="mt-2 font-display text-3xl font-bold text-ink">
              {params.id.slice(0, 8)}
            </h1>
            <p className="mt-1 text-sm text-ink-muted">
              Patient token <span className="font-mono">opaque-token</span>
              {latest && <> · last capture {fmtDateTime(latest.captured_at)}</>}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {progression?.trend && <TrendBadge trend={progression.trend} />}
            <Link
              href={`/wounds/${params.id}/mesh`}
              className="btn btn-secondary"
              title="View 3D mesh reconstruction"
            >
              3D mesh
              <span aria-hidden>→</span>
            </Link>
          </div>
        </div>

        {points.length > 0 ? (
          <>
            <section className="mt-8">
              <div className="mb-3 flex items-baseline justify-between">
                <h2 className="font-display text-lg font-semibold text-ink">Trajectory</h2>
                <span className="text-xs text-ink-muted">{points.length} captures</span>
              </div>
              <TrajectoryChart series={series} />
            </section>

            <section className="card mt-8">
              <header className="card-header">
                <div>
                  <h2 className="card-title">Measurement history</h2>
                  <p className="card-subtitle">Each row links to the signed PDF report.</p>
                </div>
              </header>
              <div className="overflow-x-auto">
                <table className="table-base">
                  <thead>
                    <tr>
                      <th>Captured</th>
                      <th className="text-right">Volume (cm³)</th>
                      <th className="text-right">Surface (cm²)</th>
                      <th className="text-right">Max depth (cm)</th>
                      <th className="text-right">Perimeter (cm)</th>
                      <th>Quality</th>
                      <th>Report</th>
                    </tr>
                  </thead>
                  <tbody>
                    {points.map((p) => (
                      <tr key={p.measurement_id}>
                        <td className="whitespace-nowrap">{fmtDateTime(p.captured_at)}</td>
                        <td className="text-right tabular-nums">{p.volume_cm3.toFixed(2)}</td>
                        <td className="text-right tabular-nums">{p.surface_area_cm2.toFixed(2)}</td>
                        <td className="text-right tabular-nums">{p.max_depth_cm.toFixed(2)}</td>
                        <td className="text-right tabular-nums">{p.perimeter_cm.toFixed(2)}</td>
                        <td>
                          <QualityPill grade={p.quality_grade} />
                        </td>
                        <td>
                          <a
                            className="text-accent hover:text-accent-bright"
                            href={`/api/proxy/measurements/${p.measurement_id}/pdf`}
                            target="_blank"
                            rel="noreferrer"
                          >
                            PDF ↗
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        ) : (
          <section className="card mt-8 p-10 text-center">
            <p className="text-sm text-ink-muted">
              No measurements captured for this wound yet. Captures from the iOS app will appear
              here once uploaded.
            </p>
          </section>
        )}

        <GraftPanel woundId={params.id} initial={grafts} />

        <NotesPanel
          woundId={params.id}
          patientToken="opaque-token"
          measurements={points}
          initial={notes}
        />

        <ReimbursementPanel
          defaultAppliedAreaCm2={latest?.surface_area_cm2}
          defaultPackageSizeCm2={latestGraft?.package_size_cm2}
        />
      </main>
    </>
  );
}

function QualityPill({ grade }: { grade: string }) {
  const map: Record<string, string> = {
    A: "pill pill-success",
    B: "pill pill-success",
    C: "pill pill-warn",
    D: "pill pill-warn",
    F: "pill pill-danger",
  };
  return <span className={map[grade] ?? "pill pill-neutral"}>{grade}</span>;
}
