import { Header } from "@/components/Header";
import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";

export default async function AuditLogPage() {
  const session = await getSession();
  if (!session || session.role !== "admin") redirect("/dashboard");

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl p-6">
        <h1 className="text-2xl font-bold">Audit log</h1>
        <p className="mt-2 text-sm text-gray-500">
          Tamper-evident chain. Each entry is hash-linked to the previous;
          tampering breaks the chain at <code>verify_chain()</code>.
        </p>
        <table className="mt-6 w-full divide-y rounded border bg-white">
          <thead className="bg-gray-100 text-sm">
            <tr>
              <th className="p-2 text-left">Time</th>
              <th className="p-2 text-left">Action</th>
              <th className="p-2 text-left">User</th>
              <th className="p-2 text-left">Resource</th>
              <th className="p-2 text-left">Hash</th>
            </tr>
          </thead>
          <tbody className="text-sm font-mono">
            <tr>
              <td className="p-2 italic text-gray-400" colSpan={5}>
                Loaded from <code>/admin/audit</code> at runtime.
              </td>
            </tr>
          </tbody>
        </table>
      </main>
    </>
  );
}
