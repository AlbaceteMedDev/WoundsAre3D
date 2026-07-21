/**
 * Text wordmark matching the logo lockup:
 * Strata (ink/white) · Metric (gold).
 * Renders crisply at any size and adapts to the active theme via tokens.
 */
export function Wordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`font-display font-bold tracking-tight ${className}`}>
      <span className="text-ink">Strata</span>
      <span style={{ color: "rgb(var(--gold))" }}>Metric</span>
    </span>
  );
}

/**
 * Full lockup: wordmark + the product line ("AI Wound Scan", cyan) and the
 * parent-brand line ("by Albacete MedDev"). Cyan is fixed per theme so it
 * stays legible on both light and dark surfaces.
 */
export function WordmarkLockup({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex flex-col leading-none ${className}`}>
      <Wordmark className="text-xl" />
      <span className="mt-1.5 text-[10px] font-semibold uppercase tracking-[0.22em] text-[#0891b2] dark:text-[#22d3ee]">
        AI Wound Scan
      </span>
      <span className="mt-1 text-[10px] font-medium uppercase tracking-[0.22em] text-ink-muted">
        by Albacete MedDev
      </span>
    </span>
  );
}
