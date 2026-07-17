import { CountUp } from "./CountUp";
import { Reveal } from "./Reveal";

const STATS = [
  { to: 60, suffix: "", decimals: 0, label: "LiDAR depth frames per 4-second burst" },
  { to: 5, suffix: "", decimals: 0, label: "measurements from a single scan", prefix: "" },
  { to: 176, suffix: "+", decimals: 0, label: "automated engine tests, six validation layers" },
  { to: 100, suffix: "%", decimals: 0, label: "of reports carry full provenance + methodology" },
];

export function StatsBand() {
  return (
    <section className="border-y border-hairline bg-surface/60">
      <div className="mk-section grid grid-cols-2 gap-8 py-12 md:grid-cols-4 md:py-14">
        {STATS.map((s, i) => (
          <Reveal key={s.label} delay={i * 90}>
            <div className="text-center md:text-left">
              <p className="font-display text-4xl font-bold tracking-tight text-ink md:text-5xl">
                <CountUp to={s.to} decimals={s.decimals} prefix={s.prefix ?? ""} suffix={s.suffix} />
              </p>
              <p className="mt-2 text-xs leading-relaxed text-ink-muted md:text-sm">{s.label}</p>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
