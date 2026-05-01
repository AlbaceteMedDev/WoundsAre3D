import { Header } from "@/components/Header";
import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";

export default async function WoundsPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl p-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Wounds</h1>
          <input
            placeholder="Filter by patient token, clinician, or wound type..."
            className="w-80 rounded border p-2 text-sm"
          />
        </div>
        <table className="mt-6 w-full divide-y rounded border bg-white">
          <thead className="bg-gray-100">
            <tr className="text-left text-sm text-gray-600">
              <th className="p-2">Patient</th>
              <th className="p-2">Wound</th>
              <th className="p-2">Type</th>
              <th className="p-2">Last measurement</th>
              <th className="p-2">Quality</th>
            </tr>
          </thead>
          <tbody>
            <tr className="text-sm">
              <td className="p-2" colSpan={5}>
                No wounds yet. Captures from the iOS app will appear here.
              </td>
            </tr>
          </tbody>
        </table>
      </main>
    </>
  );
}
