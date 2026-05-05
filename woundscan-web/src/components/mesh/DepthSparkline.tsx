"use client";

export function DepthSparkline({ series }: { series: number[] }) {
  if (series.length === 0) {
    return <div className="h-12 text-center text-[11px] text-ink-muted">No history yet</div>;
  }
  const w = 220;
  const h = 60;
  const max = Math.max(...series, 0.01);
  const min = Math.min(...series, max - 0.01);
  const range = max - min || 1;
  const step = w / Math.max(series.length - 1, 1);

  const points = series
    .map((v, i) => {
      const x = i * step;
      const y = h - ((v - min) / range) * (h - 6) - 3;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-12 w-full">
      <polyline
        points={points}
        fill="none"
        stroke="rgb(var(--accent))"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <polyline
        points={`0,${h} ${points} ${w},${h}`}
        fill="rgb(var(--accent) / 0.12)"
        stroke="none"
      />
    </svg>
  );
}
