"use client";

import {
  CartesianGrid,
  Legend,
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
    <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
      <Panel title="Volume (cm³)" data={series} dataKey="volume" stroke="#3a6cff" />
      <Panel title="Surface area (cm²)" data={series} dataKey="surfaceArea" stroke="#cc7700" />
      <Panel title="Max depth (cm)" data={series} dataKey="maxDepth" stroke="#117755" />
    </div>
  );
}

function Panel({
  title,
  data,
  dataKey,
  stroke,
}: {
  title: string;
  data: Point[];
  dataKey: keyof Point;
  stroke: string;
}) {
  return (
    <div className="rounded border bg-white p-4">
      <div className="mb-2 text-sm font-medium text-gray-700">{title}</div>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey={dataKey as string} stroke={stroke} strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
