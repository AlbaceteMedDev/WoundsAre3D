type Tone = "neutral" | "accent" | "warn" | "success" | "danger";

export function KpiTile({
  label,
  value,
  delta,
  tone = "neutral",
}: {
  label: string;
  value: string;
  delta?: string;
  tone?: Tone;
}) {
  const accentRing = {
    neutral: "border-hairline",
    accent: "border-accent/40",
    warn: "border-warn/40",
    success: "border-success/40",
    danger: "border-danger/40",
  }[tone];

  const valueColor = {
    neutral: "text-ink",
    accent: "text-ink",
    warn: "text-warn",
    success: "text-success",
    danger: "text-danger",
  }[tone];

  return (
    <div className={`card p-4 ${accentRing}`}>
      <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-muted">
        {label}
      </div>
      <div className={`mt-2 font-display text-3xl font-semibold tabular-nums ${valueColor}`}>
        {value}
      </div>
      {delta && (
        <div className="mt-1 text-[11px] text-ink-muted">
          {delta}
        </div>
      )}
    </div>
  );
}
