type Point = { x: number; y: number; label?: string };

export function Sparkline({
  data,
  height = 140,
  targetLine,
}: {
  data: Point[];
  height?: number;
  targetLine?: number;
}) {
  if (data.length === 0) return <div className="h-32 text-xs text-ink-muted">No data</div>;
  const w = 600;
  const padX = 16;
  const padTop = 12;
  const padBottom = 22;
  const ys = data.map((d) => d.y);
  const ymax = Math.max(...ys, targetLine ?? 0) * 1.2 || 1;
  const ymin = Math.min(0, ...ys);
  const range = ymax - ymin || 1;
  const xstep = (w - padX * 2) / Math.max(data.length - 1, 1);
  const yPx = (v: number) => height - padBottom - ((v - ymin) / range) * (height - padTop - padBottom);

  const path = data
    .map((d, i) => `${i === 0 ? "M" : "L"} ${(padX + i * xstep).toFixed(1)} ${yPx(d.y).toFixed(1)}`)
    .join(" ");

  const fill =
    `M ${padX} ${height - padBottom} ` +
    data.map((d, i) => `L ${(padX + i * xstep).toFixed(1)} ${yPx(d.y).toFixed(1)}`).join(" ") +
    ` L ${padX + (data.length - 1) * xstep} ${height - padBottom} Z`;

  return (
    <svg viewBox={`0 0 ${w} ${height}`} className="w-full">
      {/* Y gridlines */}
      {[0.25, 0.5, 0.75].map((t) => {
        const y = padTop + t * (height - padTop - padBottom);
        return <line key={t} x1={padX} x2={w - padX} y1={y} y2={y} stroke="rgb(var(--hairline))" strokeDasharray="2 4" />;
      })}

      {targetLine !== undefined && (
        <g>
          <line x1={padX} x2={w - padX} y1={yPx(targetLine)} y2={yPx(targetLine)} stroke="rgb(var(--warn))" strokeDasharray="4 4" />
          <text x={w - padX} y={yPx(targetLine) - 4} textAnchor="end" fontSize="10" fill="rgb(var(--warn))">
            target {targetLine}
          </text>
        </g>
      )}

      <path d={fill} fill="rgb(var(--accent) / 0.15)" />
      <path d={path} fill="none" stroke="rgb(var(--accent))" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />

      {data.map((d, i) => (
        <g key={i}>
          <circle cx={padX + i * xstep} cy={yPx(d.y)} r="3" fill="rgb(var(--accent))" />
          {d.label && (
            <text
              x={padX + i * xstep}
              y={height - 6}
              textAnchor="middle"
              fontSize="10"
              fill="rgb(var(--ink-muted))"
            >
              {d.label}
            </text>
          )}
        </g>
      ))}
    </svg>
  );
}
