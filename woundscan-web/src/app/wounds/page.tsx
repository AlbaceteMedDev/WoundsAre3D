import { Header } from "@/components/Header";
import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";

export default async function WoundsPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="flex items-center justify-between gap-4">
          <div>
            <span className="eyebrow">Cases</span>
            <h1 className="mt-2 font-display text-3xl font-bold text-ink">Wounds</h1>
          </div>
          <input
            placeholder="Filter by patient token, clinician, or wound type…"
            className="input w-80"
          />
        </div>

        <div className="card mt-6 overflow-hidden">
          <table className="table-base">
            <thead>
              <tr>
                <th>Patient</th>
                <th>Wound</th>
                <th>Type</th>
                <th>Last measurement</th>
                <th>Quality</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="text-center text-ink-muted" colSpan={5}>
                  No wounds yet. Captures from the iOS app will appear here.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </main>
    </>
  );
}
