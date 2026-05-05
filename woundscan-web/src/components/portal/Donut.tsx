type Segment = { value: number; color: string; label?: string };

export function Donut({
  segments,
  size = 120,
  thickness = 16,
  centerLabel,
  centerSub,
}: {
  segments: Segment[];
  size?: number;
  thickness?: number;
  centerLabel?: string;
  centerSub?: string;
}) {
  const r = size / 2 - thickness / 2;
  const c = 2 * Math.PI * r;
  const total = segments.reduce((a, s) => a + s.value, 0) || 1;
  let offset = 0;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <g transform={`translate(${size / 2} ${size / 2}) rotate(-90)`}>
        <circle r={r} fill="none" stroke="rgb(var(--hairline))" strokeWidth={thickness} />
        {segments.map((s, i) => {
          const len = (s.value / total) * c;
          const dash = `${len} ${c - len}`;
          const dashOffset = -offset;
          offset += len;
          return (
            <circle
              key={i}
              r={r}
              fill="none"
              stroke={s.color}
              strokeWidth={thickness}
              strokeDasharray={dash}
              strokeDashoffset={dashOffset}
              strokeLinecap="butt"
            />
          );
        })}
      </g>
      {centerLabel && (
        <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle" fontSize="18" fontWeight="700" fill="rgb(var(--ink))">
          {centerLabel}
        </text>
      )}
      {centerSub && (
        <text x="50%" y="62%" textAnchor="middle" fontSize="10" fill="rgb(var(--ink-muted))">
          {centerSub}
        </text>
      )}
    </svg>
  );
}
