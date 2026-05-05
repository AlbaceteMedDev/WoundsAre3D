import type { ProgressionTrend } from "@/lib/api";

/**
 * Big visual badge that summarises a wound's healing trajectory.
 * Healing = ≥10% area reduction since first capture.
 * Stalled = latest 21+ day window with <5% area change.
 */
export function TrendBadge({ trend }: { trend: ProgressionTrend }) {
  const status = trend.is_healing ? "healing" : trend.is_stalled ? "stalled" : "tracking";
  const config = {
    healing: { ring: "border-success/40 bg-success/10", label: "text-success", title: "Healing" },
    stalled: { ring: "border-warn/40 bg-warn/10", label: "text-warn", title: "Stalled" },
    tracking: { ring: "border-hairline bg-surface-2", label: "text-ink-soft", title: "Tracking" },
  }[status];
  const pct = trend.pct_area_change;
  const rate = trend.healing_rate_cm2_per_week;

  return (
    <div className={`rounded-lg border px-4 py-3 ${config.ring}`}>
      <p className={`text-[11px] font-semibold uppercase tracking-[0.16em] ${config.label}`}>
        {config.title}
      </p>
      <p className="mt-1 font-display text-2xl font-semibold text-ink">
        {pct !== null ? `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}% area` : "—"}
      </p>
      <p className="mt-1 text-xs text-ink-muted">
        {trend.days_observed > 0
          ? `${trend.days_observed}d observed${rate !== null ? ` · ${rate.toFixed(2)} cm²/wk closure` : ""}`
          : "Single capture"}
      </p>
    </div>
  );
}
