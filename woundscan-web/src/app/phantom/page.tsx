import { Header } from "@/components/Header";
import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";

export default async function PhantomPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  return (
    <>
      <Header />
      <main className="mx-auto max-w-3xl p-6">
        <h1 className="text-2xl font-bold">Phantom calibration</h1>
        <p className="mt-2 text-sm text-gray-500">
          Submit your monthly phantom scan. Drift alerts fire when error
          exceeds 3% volume.
        </p>
        <form
          action="/api/phantom/submit"
          method="POST"
          className="mt-6 space-y-3 rounded border bg-white p-6"
        >
          <input
            name="phantom_catalog_id"
            placeholder="Phantom ID (e.g. PHM-DFU-001)"
            className="w-full rounded border p-2"
          />
          <div className="grid grid-cols-2 gap-3">
            <input
              type="number"
              step="0.01"
              name="measured_volume_cm3"
              placeholder="Measured V (cm³)"
              className="rounded border p-2"
            />
            <input
              type="number"
              step="0.01"
              name="measured_surface_area_cm2"
              placeholder="Measured SA (cm²)"
              className="rounded border p-2"
            />
            <input
              type="number"
              step="0.01"
              name="true_volume_cm3"
              placeholder="True V (cm³)"
              className="rounded border p-2"
            />
            <input
              type="number"
              step="0.01"
              name="true_surface_area_cm2"
              placeholder="True SA (cm²)"
              className="rounded border p-2"
            />
          </div>
          <button
            type="submit"
            className="rounded bg-brand-500 px-4 py-2 text-white hover:bg-brand-600"
          >
            Submit
          </button>
        </form>
      </main>
    </>
  );
}
