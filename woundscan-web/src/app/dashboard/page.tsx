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
      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="flex items-baseline justify-between">
          <div>
            <span className="eyebrow">Overview</span>
            <h1 className="mt-2 font-display text-3xl font-bold text-ink">Dashboard</h1>
          </div>
          <span className="text-xs text-ink-muted">
            Signed in as <span className="text-ink-soft">{session.role}</span>
          </span>
        </div>

        <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-3">
          <StatCard title="Active wounds" value="0" href="/wounds" />
          <StatCard title="Pending review" value="0" href="/wounds?filter=pending" />
          <StatCard title="Phantom drift alerts" value="0" href="/phantom" />
        </div>

        <section className="mt-12">
          <h2 className="mb-3 font-display text-lg font-semibold text-ink">Recent measurements</h2>
          <div className="card p-6">
            <p className="text-sm text-ink-muted">
              Recent measurements will appear here once captures are uploaded from the iOS app.
            </p>
          </div>
        </section>
      </main>
    </>
  );
}

function StatCard({ title, value, href }: { title: string; value: string; href: string }) {
  return (
    <Link
      href={href}
      className="card group block p-5 transition hover:border-accent/60 hover:shadow-elevated"
    >
      <div className="text-xs uppercase tracking-[0.14em] text-ink-muted">{title}</div>
      <div className="mt-3 font-display text-3xl font-semibold text-ink">{value}</div>
      <div className="mt-3 text-xs text-accent opacity-0 transition group-hover:opacity-100">
        View →
      </div>
    </Link>
  );
}
