/**
 * Text wordmark matching the logo lockup:
 * Strata (ink) · Metric (blue/cyan) · AI (ink, fine gold hairline beneath).
 * Gold appears only as the hairline — jewelry, not letterforms.
 * Renders crisply at any size and adapts to the active theme via tokens.
 */
export function Wordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`font-display font-bold tracking-tight ${className}`}>
      <span className="text-ink">Strata</span>
      <span style={{ color: "rgb(var(--wm-metric))" }}>Metric</span>{" "}
      <span className="relative inline-block text-ink">
        AI
        <span
          aria-hidden
          className="absolute -bottom-[0.12em] left-0 right-0 h-[0.075em] min-h-[2px] rounded-full"
          style={{
            background:
              "linear-gradient(90deg, rgb(var(--gold) / 0.55), rgb(var(--gold)), rgb(var(--gold) / 0.55))",
          }}
        />
      </span>
    </span>
  );
}

export function WordmarkLockup({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex flex-col ${className}`}>
      <Wordmark className="text-xl leading-none" />
      <span className="mt-1.5 text-[10px] font-medium uppercase tracking-[0.22em] text-ink-muted">
        by Albacete MedDev
      </span>
    </span>
  );
}
