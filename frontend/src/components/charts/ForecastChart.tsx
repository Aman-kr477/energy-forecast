// src/components/charts/ForecastChart.tsx
// Line chart: forecast MW across the delivery day, with optional actuals overlay
// and P10/P90 error band shading.
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ForecastSlot, ErrorBand } from "@/types/api";
import { fmtTime, fmtMW } from "@/lib/utils";
import { ChartSkeleton } from "@/components/common/ChartSkeleton";
import { EmptyState } from "@/components/common/EmptyState";

interface Props {
  slots: ForecastSlot[];
  errorBand: ErrorBand;
  showActuals: boolean;
  loading?: boolean;
}

export function ForecastChart({ slots, errorBand, showActuals, loading }: Props) {
  if (loading) return <ChartSkeleton height={320} />;
  if (!slots.length) return <EmptyState message="No forecast data for this date." />;

  const hasBand = errorBand.p10_mw != null && errorBand.p90_mw != null;

  const data = slots.map((s) => {
    const fcst = s.forecast_mw ?? undefined;
    const p10 = hasBand && fcst != null ? fcst + errorBand.p10_mw! : undefined;
    const p90 = hasBand && fcst != null ? fcst + errorBand.p90_mw! : undefined;
    return {
      time: fmtTime(s.start_time),
      forecast: fcst,
      actual: showActuals ? (s.actual_mw ?? undefined) : undefined,
      bandLow: p10,
      bandHigh: p90,
      // For the Area fill we need [low, high-low] representation via two Areas stacked
      bandBase: p10,
      bandSpan: p10 != null && p90 != null ? p90 - p10 : undefined,
    };
  });

  return (
    <ResponsiveContainer width="100%" height={320}>
      <ComposedChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="time" tick={{ fontSize: 11 }} interval={5} />
        <YAxis
          tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
          tick={{ fontSize: 11 }}
          label={{ value: "MW", angle: -90, position: "insideLeft", style: { fontSize: 11 } }}
        />
        <Tooltip
          formatter={(value, name) => [fmtMW(value as number), String(name)]}
          labelFormatter={(l) => `${l} UTC`}
          contentStyle={{ fontSize: 12 }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />

        {/* Error band: transparent base Area + coloured span Area stacked */}
        {hasBand && (
          <>
            <Area
              dataKey="bandBase"
              stroke="none"
              fill="transparent"
              legendType="none"
              isAnimationActive={false}
            />
            <Area
              dataKey="bandSpan"
              stackId="band"
              stroke="none"
              fill="#93c5fd"
              fillOpacity={0.3}
              name="P10–P90 error band"
              isAnimationActive={false}
            />
          </>
        )}

        <Line
          dataKey="forecast"
          stroke="#2563eb"
          strokeWidth={2}
          dot={false}
          name="Forecast MW"
          isAnimationActive={false}
        />
        {showActuals && (
          <Line
            dataKey="actual"
            stroke="#059669"
            strokeWidth={2}
            dot={false}
            strokeDasharray="4 2"
            name="Actual MW"
            isAnimationActive={false}
          />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
}

