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
      <main className="mx-auto max-w-3xl px-6 py-16">
        <span className="eyebrow">Provider portal</span>
        <h1 className="mt-3 font-display text-4xl font-bold tracking-tight text-ink md:text-5xl">
          Wound capture, progression, and reimbursement —{" "}
          <em className="not-italic text-accent">one workflow.</em>
        </h1>
        <p className="mt-4 text-base leading-relaxed text-ink-soft">
          Clinical decision support for wound measurement, healing trajectory, UDI-traceable graft
          applications, and Medicare reimbursement estimates. Sign in to access patient cases.
        </p>
        <div className="mt-8 flex gap-3">
          <Link href="/login" className="btn btn-primary">
            Sign in
            <span aria-hidden>→</span>
          </Link>
          <a
            href="https://albacetemeddev.com"
            target="_blank"
            rel="noreferrer"
            className="btn btn-secondary"
          >
            About Albacete MedDev
          </a>
        </div>
        <p className="mt-12 text-xs leading-relaxed text-ink-muted">
          For clinical decision support only. Not for diagnostic use. Clinician retains decision
          authority. Methodology disclosed in every report.
        </p>
      </main>
    </>
  );
}
