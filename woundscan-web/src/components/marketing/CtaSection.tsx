import Link from "next/link";
import { Reveal } from "./Reveal";
import { Wordmark } from "./Wordmark";

export function CtaSection() {
  return (
    <section className="relative overflow-hidden py-24 md:py-32">
      <div aria-hidden className="mk-grid-bg absolute inset-0" />
      <div
        aria-hidden
        className="absolute left-1/2 top-1/2 h-[420px] w-[720px] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-30 blur-3xl"
        style={{ background: "radial-gradient(closest-side, rgb(var(--accent) / 0.4), transparent 70%)" }}
      />
      <div className="mk-section relative text-center">
        <Reveal>
          <Wordmark className="text-3xl md:text-4xl" />
          <h2 className="mx-auto mt-6 max-w-3xl font-display text-3xl font-bold tracking-tight text-ink md:text-5xl md:leading-[1.1]">
            See the platform with your own cases.
          </h2>
          <p className="mx-auto mt-5 max-w-xl text-base leading-relaxed text-ink-soft md:text-lg">
            Providers with an account can sign in to the portal now. If you&rsquo;d like access — or a
            guided walkthrough for your practice, network, or investment team — we&rsquo;ll set it up.
          </p>
          <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
            <Link href="/login" className="btn btn-primary px-6 py-3 text-base">
              Portal sign in
              <span aria-hidden>→</span>
            </Link>
            <a
              href="mailto:gabe@albacetemeddev.com?subject=StrataMetric%20AI%20access%20request"
              className="btn btn-secondary px-6 py-3 text-base"
            >
              Request access
            </a>
            <a href="#demo" className="btn btn-ghost px-4 py-3 text-base">
              Replay the demo
            </a>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
