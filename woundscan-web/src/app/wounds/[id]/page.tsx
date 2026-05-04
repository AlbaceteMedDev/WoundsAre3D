import { Header } from "@/components/Header";
import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";
import { TrajectoryChart } from "@/components/TrajectoryChart";

export default async function WoundDetailPage({ params }: { params: { id: string } }) {
  const session = await getSession();
  if (!session) redirect("/login");

  // In production: fetch /wounds/{id} and /measurements?wound_id={id}
  const sampleSeries = [
    { date: "2026-04-01", volume: 4.5, surfaceArea: 8.0, maxDepth: 1.0 },
    { date: "2026-04-08", volume: 3.8, surfaceArea: 7.4, maxDepth: 0.9 },
    { date: "2026-04-15", volume: 3.0, surfaceArea: 6.5, maxDepth: 0.7 },
    { date: "2026-04-22", volume: 2.4, surfaceArea: 5.8, maxDepth: 0.6 },
  ];

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl p-6">
        <h1 className="text-2xl font-bold">Wound {params.id}</h1>
        <p className="text-sm text-gray-500">Patient: opaque-token</p>

        <section className="mt-8">
          <h2 className="mb-4 text-lg font-semibold">Trajectory</h2>
          <TrajectoryChart series={sampleSeries} />
        </section>

        <section className="mt-8">
          <h2 className="mb-4 text-lg font-semibold">Measurements</h2>
          <table className="w-full divide-y rounded border bg-white">
            <thead className="bg-gray-100 text-sm text-gray-600">
              <tr>
                <th className="p-2 text-left">Date</th>
                <th className="p-2 text-left">V (cm³)</th>
                <th className="p-2 text-left">SA (cm²)</th>
                <th className="p-2 text-left">Max depth (cm)</th>
                <th className="p-2 text-left">Quality</th>
                <th className="p-2 text-left"></th>
              </tr>
            </thead>
            <tbody>
              {sampleSeries.map((m) => (
                <tr key={m.date} className="border-t text-sm">
                  <td className="p-2">{m.date}</td>
                  <td className="p-2">{m.volume.toFixed(2)}</td>
                  <td className="p-2">{m.surfaceArea.toFixed(2)}</td>
                  <td className="p-2">{m.maxDepth.toFixed(2)}</td>
                  <td className="p-2">A</td>
                  <td className="p-2">
                    <a className="text-brand-600 underline" href="#">
                      View report
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </main>
    </>
  );
}
