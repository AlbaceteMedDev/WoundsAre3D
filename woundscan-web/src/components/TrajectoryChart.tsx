"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Point = {
  date: string;
  volume: number;
  surfaceArea: number;
  maxDepth: number;
};

export function TrajectoryChart({ series }: { series: Point[] }) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      <Panel title="Volume" unit="cm³" data={series} dataKey="volume" />
      <Panel title="Surface area" unit="cm²" data={series} dataKey="surfaceArea" />
      <Panel title="Max depth" unit="cm" data={series} dataKey="maxDepth" />
    </div>
  );
}

function Panel({
  title,
  unit,
  data,
  dataKey,
}: {
  title: string;
  unit: string;
  data: Point[];
  dataKey: keyof Point;
}) {
  return (
    <div className="card p-4">
      <div className="mb-3 flex items-baseline justify-between">
        <span className="text-sm font-medium text-ink">{title}</span>
        <span className="text-xs text-ink-muted">{unit}</span>
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={data} margin={{ left: -10, right: 8, top: 4, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgb(var(--hairline))" />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: "rgb(var(--ink-muted))" }} stroke="rgb(var(--hairline))" />
          <YAxis tick={{ fontSize: 11, fill: "rgb(var(--ink-muted))" }} stroke="rgb(var(--hairline))" width={36} />
          <Tooltip
            contentStyle={{
              background: "rgb(var(--surface))",
              border: "1px solid rgb(var(--hairline))",
              borderRadius: 8,
              color: "rgb(var(--ink))",
              fontSize: 12,
            }}
            labelStyle={{ color: "rgb(var(--ink-muted))" }}
            cursor={{ stroke: "rgb(var(--accent))", strokeWidth: 1 }}
          />
          <Line
            type="monotone"
            dataKey={dataKey as string}
            stroke="rgb(var(--accent))"
            strokeWidth={2}
            dot={{ r: 3, fill: "rgb(var(--accent))" }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
