import { Reveal } from "./Reveal";

/**
 * Partnership credential. The architecture section directly above shows *what*
 * runs on AWS; this says *who built it and with whose backing* — the part a
 * clinician or investor uses to decide whether an early-stage platform is
 * credible. Deliberately understated: named partner, verifiable designations,
 * no logos we don't have permission to reproduce.
 */
const COMPETENCIES = ["DevOps", "Data & Analytics", "Migration", "SaaS"];

const FACTS = [
  {
    k: "Premier tier",
    v: "nClouds holds AWS Premier Consulting Partner status — the top tier of the AWS Partner Network, held by a small fraction of partners worldwide.",
  },
  {
    k: "Healthcare AI/ML delivery",
    v: "A track record of production AI and machine-learning workloads on AWS for healthcare and life-sciences customers, not a first attempt at a regulated domain.",
  },
  {
    k: "AWS-backed build",
    v: "The proof of concept was delivered with AWS partner funding support, which is awarded against a reviewed technical scope rather than a pitch deck.",
  },
];

export function PartnershipSection() {
  return (
    <section id="partnership" className="relative scroll-mt-20 py-20 md:py-28">
      <div className="mk-section">
        <div className="grid gap-12 lg:grid-cols-[1.05fr_1fr] lg:items-start lg:gap-16">
          <Reveal>
            <div>
              <span className="eyebrow">Partnership</span>
              <h2 className="mk-h2 mt-3">
                Built with nClouds,{" "}
                <span className="text-gradient">backed by AWS.</span>
              </h2>
              <p className="mk-lead">
                The measurement pipeline was designed and built with{" "}
                <a
                  href="https://www.nclouds.com"
                  target="_blank"
                  rel="noreferrer"
                  className="font-medium text-ink underline decoration-accent/40 underline-offset-4 transition hover:decoration-accent"
                >
                  nClouds
                </a>
                , an AWS Premier Consulting Partner, under an AWS-funded proof of concept. Two
                engineering teams reviewed the same architecture before a single wound was scanned —
                the serverless ingest, the segmentation and narration services, and the encryption
                and key management shown above.
              </p>
              <p className="mt-4 max-w-2xl text-base leading-relaxed text-ink-soft">
                That matters for a reason that has nothing to do with logos. Early-stage clinical
                software usually asks you to trust a demo. This one was scoped, built and reviewed
                against AWS engineering standards, and the architecture that carried the proof of
                concept is the architecture that carries production.
              </p>

              <ul
                className="mt-8 flex flex-wrap items-center gap-2"
                aria-label="nClouds AWS competencies"
              >
                {COMPETENCIES.map((c) => (
                  <li key={c} className="mk-chip">
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          </Reveal>

          <Reveal delay={120}>
            <ul className="grid gap-4">
              {FACTS.map((f) => (
                <li key={f.k} className="mk-tile">
                  <p className="font-display text-sm font-semibold text-ink">{f.k}</p>
                  <p className="mt-2 text-sm leading-relaxed text-ink-soft">{f.v}</p>
                </li>
              ))}
            </ul>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
