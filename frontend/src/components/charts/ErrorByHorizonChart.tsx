// src/components/charts/ErrorByHorizonChart.tsx
// Bar chart of MAE by forecast horizon bucket.
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { HorizonMetric } from "@/types/api";
import { ChartSkeleton } from "@/components/common/ChartSkeleton";
import { EmptyState } from "@/components/common/EmptyState";

interface Props { data: HorizonMetric[]; loading?: boolean; }

export function ErrorByHorizonChart({ data, loading }: Props) {
  if (loading) return <ChartSkeleton height={240} />;
  if (!data.length) return <EmptyState message="No horizon data available." />;

  const chartData = data.map((d) => ({ horizon: `${d.horizon_hours}h`, mae: Math.round(d.mae) }));

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="horizon" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} label={{ value: "MAE (MW)", angle: -90, position: "insideLeft", style: { fontSize: 11 } }} />
        <Tooltip formatter={(v) => [`${(v as number).toLocaleString()} MW`, "MAE"]} contentStyle={{ fontSize: 12 }} />
        <Bar dataKey="mae" fill="#2563eb" radius={[3, 3, 0, 0]} name="MAE" />
      </BarChart>
    </ResponsiveContainer>
  );
}

