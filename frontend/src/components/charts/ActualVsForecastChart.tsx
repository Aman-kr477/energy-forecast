// src/components/charts/ActualVsForecastChart.tsx
// Line chart of actual vs forecast MW over a date range.
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
import type { TimeSeriesPoint } from "@/types/api";
import { fmtDateTime, fmtMW } from "@/lib/utils";
import { ChartSkeleton } from "@/components/common/ChartSkeleton";
import { EmptyState } from "@/components/common/EmptyState";

interface Props { data: TimeSeriesPoint[]; loading?: boolean; }

export function ActualVsForecastChart({ data, loading }: Props) {
  if (loading) return <ChartSkeleton height={280} />;
  if (!data.length) return <EmptyState message="No data for selected range and horizon." />;

  // Sample down to every 4th point so the chart stays readable over 30 days
  const sampled = data.filter((_, i) => i % 4 === 0);

  const chartData = sampled.map((d) => ({
    time: fmtDateTime(d.start_time),
    actual: d.actual_mw ?? undefined,
    forecast: d.forecast_mw ?? undefined,
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="time" tick={{ fontSize: 10 }} interval={23} />
        <YAxis
          tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
          tick={{ fontSize: 11 }}
          label={{ value: "MW", angle: -90, position: "insideLeft", style: { fontSize: 11 } }}
        />
        <Tooltip formatter={(v, n) => [fmtMW(v as number), String(n)]} contentStyle={{ fontSize: 12 }} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line dataKey="forecast" stroke="#2563eb" strokeWidth={1.5} dot={false} name="Forecast MW" isAnimationActive={false} />
        <Line dataKey="actual" stroke="#059669" strokeWidth={1.5} dot={false} name="Actual MW" isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

