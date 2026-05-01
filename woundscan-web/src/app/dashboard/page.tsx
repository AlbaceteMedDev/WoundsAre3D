import { Header } from "@/components/Header";
import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";
import Link from "next/link";

export default async function DashboardPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl p-6">
        <h1 className="mb-6 text-2xl font-bold">Dashboard</h1>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Card title="Active wounds" value="0" href="/wounds" />
          <Card title="Pending review" value="0" href="/wounds?filter=pending" />
          <Card title="Phantom drift alerts" value="0" href="/phantom" />
        </div>
        <section className="mt-12">
          <h2 className="mb-4 text-xl font-semibold">Recent measurements</h2>
          <p className="text-sm text-gray-500">
            Recent measurements will appear here once captures are uploaded.
          </p>
        </section>
      </main>
    </>
  );
}

function Card({ title, value, href }: { title: string; value: string; href: string }) {
  return (
    <Link
      href={href as `/${string}`}
      className="block rounded-lg border bg-white p-4 shadow-sm hover:shadow-md"
    >
      <div className="text-sm text-gray-500">{title}</div>
      <div className="mt-2 text-2xl font-semibold">{value}</div>
    </Link>
  );
}
