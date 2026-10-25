// src/components/charts/ErrorHistogram.tsx
// Bar chart of forecast error distribution.
import {
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { HistogramBin } from "@/types/api";
import { ChartSkeleton } from "@/components/common/ChartSkeleton";
import { EmptyState } from "@/components/common/EmptyState";

interface Props { bins: HistogramBin[]; loading?: boolean; }

export function ErrorHistogram({ bins, loading }: Props) {
  if (loading) return <ChartSkeleton height={240} />;
  if (!bins.length) return <EmptyState message="No error distribution data." />;

  const chartData = bins.map((b) => ({
    label: `${Math.round(b.bin_left / 100) * 100}`,
    count: b.count,
    mid: (b.bin_left + b.bin_right) / 2,
  }));

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="label" tick={{ fontSize: 10 }} label={{ value: "Error (MW)", position: "insideBottom", offset: -2, style: { fontSize: 11 } }} />
        <YAxis tick={{ fontSize: 11 }} label={{ value: "Count", angle: -90, position: "insideLeft", style: { fontSize: 11 } }} />
        <Tooltip
          formatter={(v) => [v as number, "slots"]}
          labelFormatter={(l) => `~${Number(l).toLocaleString()} MW error`}
          contentStyle={{ fontSize: 12 }}
        />
        <ReferenceLine x="0" stroke="#94a3b8" strokeDasharray="4 2" />
        <Bar dataKey="count" fill="#7c3aed" radius={[2, 2, 0, 0]} name="Count" />
      </BarChart>
    </ResponsiveContainer>
  );
}

