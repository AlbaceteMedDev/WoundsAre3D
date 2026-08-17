import { Reveal } from "./Reveal";

/**
 * The orientation section. Most first-time visitors arrive from a link someone
 * texted them, with no context beyond the preview card — so before the site
 * argues *why now* or shows *how the engine works*, this states plainly what
 * the product is and everything it covers, in one scannable pass.
 */
const CAPABILITIES = [
  {
    n: "01",
    title: "Four-second capture",
    body: "A clinician points an iPhone. A LiDAR burst collects 60 depth frames in about four seconds — no rulers, no disposable markers, no probe in the wound bed.",
  },
  {
    n: "02",
    title: "Volume, integrated — not estimated",
    body: "Most tools multiply length × width × depth and call it volume. The engine integrates the depth field across the whole wound bed, so an undermined or irregular wound reports the volume it actually has — with surface area, true depth and perimeter, each carrying a 95% confidence interval.",
  },
  {
    n: "03",
    title: "Documentation that defends itself",
    body: "Notes and measurement reports generate themselves, carrying methodology and provenance, and lock with a signature inside the 48-hour window auditors look for.",
  },
  {
    n: "04",
    title: "Claims & compliance",
    body: "HCPCS verification, LCD/NCD alignment, photo and 3D evidence, medical-necessity narratives — scored continuously on every open case instead of discovered at audit.",
  },
  {
    n: "05",
    title: "Graft inventory with UDI",
    body: "Serial, lot and UDI captured at the point of care, so every graft unit is traceable from manufacturer to application to the claim it was billed on.",
  },
  {
    n: "06",
    title: "The service line around it",
    body: "Patient and wound tracking with healing trajectories, stalled-wound flags, reporting and analytics, route planning for mobile teams, and a tamper-evident audit chain.",
  },
];

export function AtAGlanceSection() {
  return (
    <section id="overview" className="relative scroll-mt-20 py-20 md:py-28">
      <div className="mk-section">
        <Reveal>
          <div className="max-w-3xl">
            <span className="eyebrow">What it is</span>
            <h2 className="mk-h2 mt-3">
              A measurement instrument — and the{" "}
              <span className="text-gradient">service line built around it.</span>
            </h2>
            <p className="mk-lead">
              AI Wound Scan replaces the ruler-and-photo workflow with an objective 3D measurement
              taken at the bedside, then carries that measurement all the way through the
              documentation, compliance and supply chain that a wound program actually gets paid on.
            </p>
          </div>
        </Reveal>

        <div className="mt-12 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {CAPABILITIES.map((c, i) => (
            <Reveal key={c.n} delay={i * 70}>
              <article className="mk-tile h-full">
                <span className="mk-tile-index">{c.n}</span>
                <h3 className="mt-4 font-display text-base font-semibold text-ink">{c.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-soft">{c.body}</p>
              </article>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
