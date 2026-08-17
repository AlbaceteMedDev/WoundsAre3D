import { Reveal } from "./Reveal";

const BENEFITS = [
  {
    n: "01",
    title: "Revenue protection",
    body: "Objective, instrument-derived measurements create documentation that substantiates billed wound dimensions under CMS audit scrutiny — reducing the claim-denial risk that has hit practices relying on manual tracing.",
  },
  {
    n: "02",
    title: "Clinical differentiation",
    body: "Non-rectangular wound bed area, true depth, and peri-wound area in a single scan — the full three-dimensional wound profile, captured at the point of care. No consumer or clinical smartphone tool offers this today.",
  },
  {
    n: "03",
    title: "Operational efficiency",
    body: "One scan replaces manual measurement, photography, diagram drawing, and manual entry. Automated measurement and diagram generation hands hours back to clinicians and documentation staff every week.",
  },
  {
    n: "04",
    title: "Investor & partner narrative",
    body: "A working demonstration of LiDAR wound measurement on AWS, built with an AWS Premier Partner, is concrete technical evidence — for fundraising, clinical partnerships, and the regulatory conversations that follow a successful proof of concept.",
  },
];

export function BenefitsSection() {
  return (
    <section className="relative py-20 md:py-28">
      <div className="mk-section">
        <Reveal>
          <span className="eyebrow">Why it wins</span>
          <h2 className="mk-h2 mt-3">Strategic value on four fronts.</h2>
        </Reveal>

        <div className="mt-12 grid gap-x-10 gap-y-10 md:grid-cols-2">
          {BENEFITS.map((b, i) => (
            <Reveal key={b.n} delay={(i % 2) * 110}>
              <article className="group relative border-t border-hairline pt-6">
                <span
                  aria-hidden
                  className="absolute -top-px left-0 h-px w-0 bg-accent transition-all duration-500 group-hover:w-full"
                />
                <p className="font-mono text-xs text-accent">{b.n}</p>
                <h3 className="mt-2 font-display text-xl font-semibold text-ink">{b.title}</h3>
                <p className="mt-2.5 max-w-lg text-sm leading-relaxed text-ink-soft">{b.body}</p>
              </article>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
