import { Reveal } from "./Reveal";

const ITEMS = [
  {
    title: "Clinical decision support posture",
    body: "Operates today under the 21st Century Cures Act §3060 CDS exemption: the clinician retains decision authority, no diagnostic claims are made, and the measurement methodology is transparently displayed in every report.",
  },
  {
    title: "510(k)-ready architecture",
    body: "Designed to support an FDA 510(k) submission without rewrite: a bidirectional regulatory traceability matrix, versioned algorithms, and a comprehensive validation harness are part of the codebase — not an afterthought.",
  },
  {
    title: "HIPAA-grade controls",
    body: "TOTP multi-factor authentication, role-based access, tamper-evident audit hash chain, encryption at rest and in transit with managed key rotation, and hardened security headers across the portal.",
  },
  {
    title: "Retention engineered in",
    body: "Object-locked storage with six-year retention, multi-AZ encrypted databases, VPC isolation with flow logs, and continuous monitoring via CloudWatch, GuardDuty, and Security Hub in the production architecture.",
  },
];

export function ComplianceSection() {
  return (
    <section id="compliance" className="relative scroll-mt-20 border-y border-hairline bg-surface/40 py-20 md:py-28">
      <div className="mk-section">
        <div className="grid gap-10 lg:grid-cols-[440px_1fr]">
          <Reveal>
            <div className="lg:sticky lg:top-28">
              <span className="eyebrow">Compliance & trust</span>
              <h2 className="mk-h2 mt-3">Regulatory strategy is an architecture decision.</h2>
              <p className="mk-lead">
                StrataMetric&rsquo;s AI Wound Scan was engineered from the first commit for the pathway ahead —
                internal clinical-decision-support use now, commercial clearance later, with no
                rewrite in between.
              </p>
              <div className="mt-8 flex flex-wrap gap-2">
                <span className="mk-chip">Cures Act §3060 CDS</span>
                <span className="mk-chip">FDA 510(k)-ready</span>
                <span className="mk-chip">HIPAA-grade controls</span>
                <span className="mk-chip">6-year retention</span>
              </div>
            </div>
          </Reveal>

          <div className="space-y-4">
            {ITEMS.map((it, i) => (
              <Reveal key={it.title} delay={i * 90}>
                <article className="mk-card flex gap-4">
                  <span className="mt-1 grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-accent/10 text-accent">
                    <ShieldIcon />
                  </span>
                  <div>
                    <h3 className="font-display text-base font-semibold text-ink">{it.title}</h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-ink-soft">{it.body}</p>
                  </div>
                </article>
              </Reveal>
            ))}
            <Reveal delay={380}>
              <p className="px-1 text-[11px] leading-relaxed text-ink-muted">
                For clinical decision support only. Not for diagnostic use. Clinician retains
                decision authority. Methodology disclosed in every measurement report.
              </p>
            </Reveal>
          </div>
        </div>
      </div>
    </section>
  );
}

function ShieldIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden>
      <path
        d="M10 2l6.5 2.4v4.9c0 4.1-2.8 7.2-6.5 8.7-3.7-1.5-6.5-4.6-6.5-8.7V4.4L10 2z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path d="M7 9.8l2.2 2.2L13.5 7.6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
