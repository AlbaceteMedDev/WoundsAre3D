import { Header } from "@/components/Header";
import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";

export default async function ProductsAdminPage() {
  const session = await getSession();
  if (!session) redirect("/login");
  if (session.role !== "admin") redirect("/dashboard");

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl p-6">
        <h1 className="text-2xl font-bold">Product database</h1>
        <p className="mt-2 text-sm text-gray-500">
          Add, edit, and version-control IFU overlap and stock sizes.
        </p>
        <table className="mt-6 w-full divide-y rounded border bg-white">
          <thead className="bg-gray-100 text-sm">
            <tr>
              <th className="p-2 text-left">ID</th>
              <th className="p-2 text-left">Name</th>
              <th className="p-2 text-left">Manufacturer</th>
              <th className="p-2 text-left">δ (cm)</th>
              <th className="p-2 text-left">Stock sizes (cm²)</th>
              <th className="p-2 text-left">Indications</th>
            </tr>
          </thead>
          <tbody className="text-sm">
            <tr>
              <td className="p-2 italic text-gray-400" colSpan={6}>
                Loaded from <code>/admin/products</code> at runtime.
              </td>
            </tr>
          </tbody>
        </table>
      </main>
    </>
  );
}
