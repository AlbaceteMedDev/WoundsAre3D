import Link from "next/link";
import { Header } from "@/components/Header";
import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";

export default async function HomePage() {
  const session = await getSession();
  if (session) redirect("/dashboard");

  return (
    <>
      <Header />
      <main className="mx-auto max-w-3xl p-8">
        <h1 className="text-3xl font-bold">WoundScan Dashboard</h1>
        <p className="mt-4 text-gray-600">
          Clinical decision support platform for wound measurement, trajectory
          analysis, and graft selection. Sign in to access patient data.
        </p>
        <Link
          href="/login"
          className="mt-6 inline-block rounded bg-brand-500 px-4 py-2 text-white hover:bg-brand-600"
        >
          Sign in
        </Link>
        <p className="mt-12 text-sm text-gray-500">
          For clinical decision support only. Not for diagnostic use. Clinician
          retains decision authority. Methodology disclosed in every report.
        </p>
      </main>
    </>
  );
}
