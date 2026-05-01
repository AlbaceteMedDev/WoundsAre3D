import { Header } from "@/components/Header";
import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";

export default async function MLMetricsPage() {
  const session = await getSession();
  if (!session || session.role !== "admin") redirect("/dashboard");

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl p-6">
        <h1 className="text-2xl font-bold">ML model metrics</h1>
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
          <Stat label="Boundary IoU (rolling)" value="—" />
          <Stat label="Tissue macro F1" value="—" />
          <Stat label="Probe detection recall" value="—" />
        </div>
        <section className="mt-8">
          <h2 className="text-lg font-semibold">Drift alerts</h2>
          <p className="text-sm text-gray-500">
            None at present. Alerts trigger when a model's rolling validation
            metric drops &gt;3% from the deployed baseline.
          </p>
        </section>
      </main>
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border bg-white p-4">
      <div className="text-sm text-gray-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
    </div>
  );
}
