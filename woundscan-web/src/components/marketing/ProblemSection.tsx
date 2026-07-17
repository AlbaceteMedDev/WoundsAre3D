import { Reveal } from "./Reveal";

const CARDS = [
  {
    title: "The ruler and the guess",
    body: "Most practices still measure wounds with a disposable ruler, a tracing, and a photograph. The result is subjective, inconsistent between providers, and has proven inadequate under Medicare audit.",
    icon: RulerIcon,
  },
  {
    title: "Photos are flat",
    body: "Photograph-based tools can't capture depth — the dimension most clinically significant for wound severity and product sizing. Claims built on 2D documentation have faced denials when the billed graft area couldn't be substantiated.",
    icon: PhotoIcon,
  },
  {
    title: "Reimbursement changed",
    body: "Medicare payment for wound graft procedures has declined substantially per square centimeter. Accurate documentation of dimensions — especially depth and peri-wound area — is now directly material to revenue and audit defensibility.",
    icon: TrendIcon,
  },
];

export function ProblemSection() {
  return (
    <section className="relative py-20 md:py-28">
      <div className="mk-section">
        <Reveal>
          <span className="eyebrow">Why now</span>
          <h2 className="mk-h2 mt-3">
            Documentation is no longer a clinical nicety.
            <br className="hidden md:block" />
            <span className="text-gradient"> It&rsquo;s a revenue driver and an audit requirement.</span>
          </h2>
          <p className="mk-lead">
            The gap between what current tools provide and what CMS now requires has created a
            clear opening for an objective, instrument-based measurement platform.
          </p>
        </Reveal>

        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {CARDS.map((c, i) => (
            <Reveal key={c.title} delay={i * 110}>
              <article className="mk-card h-full">
                <span className="grid h-11 w-11 place-items-center rounded-lg bg-accent/10 text-accent">
                  <c.icon />
                </span>
                <h3 className="mt-5 font-display text-lg font-semibold text-ink">{c.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-soft">{c.body}</p>
              </article>
            </Reveal>
          ))}
        </div>

        <Reveal delay={140}>
          <p className="mx-auto mt-12 max-w-3xl text-center font-display text-xl font-medium leading-relaxed text-ink md:text-2xl">
            &ldquo;The same measurement every time the same wound is scanned — by any clinician, on any
            day. <span className="text-accent">That reproducibility is what makes documentation
            audit-defensible.</span>&rdquo;
          </p>
        </Reveal>
      </div>
    </section>
  );
}

function RulerIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden>
      <rect x="2" y="7" width="16" height="6" rx="1" stroke="currentColor" strokeWidth="1.5" />
      <path d="M5.5 7v2.5M8.5 7v2.5M11.5 7v2.5M14.5 7v2.5" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}
function PhotoIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden>
      <rect x="2.5" y="4" width="15" height="12" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="7" cy="8.5" r="1.4" stroke="currentColor" strokeWidth="1.2" />
      <path d="M4 14.5l4-3.5 3 2.5 3-3 2.5 2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
function TrendIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden>
      <path d="M3 5l5 5 3-3 6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M17 9.5V13h-3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
