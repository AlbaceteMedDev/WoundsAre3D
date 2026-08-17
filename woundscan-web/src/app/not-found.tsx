import type { Metadata } from "next";
import Link from "next/link";
import { BrandImage } from "@/components/BrandImage";

export const metadata: Metadata = {
  title: "Page not found",
  robots: { index: false, follow: true },
};

/**
 * A mistyped or truncated shared link previously fell through to the framework
 * default, which rendered an unbranded page still wearing the homepage's
 * preview tags. This gives that visitor a way back in.
 */
export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-screen max-w-lg flex-col justify-center px-6 py-16 text-center">
      <Link href="/" aria-label="StrataMetric — AI Wound Scan home" className="mx-auto">
        <BrandImage
          variant="lockup"
          alt="StrataMetric — AI Wound Scan by Albacete MedDev"
          priority
          className="h-auto w-56"
        />
      </Link>

      <p className="mt-10 font-mono text-[11px] uppercase tracking-[0.2em] text-ink-muted">
        Error 404
      </p>
      <h1 className="mt-3 font-display text-3xl font-bold tracking-tight text-ink">
        That page doesn&rsquo;t exist.
      </h1>
      <p className="mt-4 text-sm leading-relaxed text-ink-soft">
        The link may have been truncated on its way to you. The overview of what AI Wound Scan
        does is on the home page, and the 3D viewer runs without an account.
      </p>

      <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
        <Link href="/" className="btn btn-primary px-5 py-2.5">
          Go to the overview
          <span aria-hidden>→</span>
        </Link>
        <Link href="/demo" className="btn btn-secondary px-5 py-2.5">
          Open the 3D demo
        </Link>
      </div>
    </main>
  );
}
