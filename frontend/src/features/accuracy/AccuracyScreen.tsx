// src/features/accuracy/AccuracyScreen.tsx
// Screen 2: "Forecast accuracy"
// Date range + horizon → metric cards + 3 charts.
import { useEffect } from "react";
import { api } from "@/lib/api";
import { useApiCall } from "@/hooks/useApi";
import { useAccuracyStore } from "@/store/filterStore";
import { ActualVsForecastChart } from "@/components/charts/ActualVsForecastChart";
import { ErrorByHorizonChart } from "@/components/charts/ErrorByHorizonChart";
import { ErrorHistogram } from "@/components/charts/ErrorHistogram";
import { MetricCard } from "@/components/common/MetricCard";
import { Alert } from "@/components/ui/alert";
import { TimezoneBadge } from "@/components/common/TimezoneBadge";
import { fmtMW, fmtSigned, fmtPct, biasCaptionText } from "@/lib/utils";
import type { MetaResponse } from "@/types/api";

interface Props { meta: MetaResponse }

export function AccuracyScreen({ meta }: Props) {
  const { startDate, endDate, horizon, setStartDate, setEndDate, setHorizon } =
    useAccuracyStore();

  // Default to full January range
  useEffect(() => {
    if (!startDate && meta.delivery_dates.length) {
      setStartDate(meta.delivery_dates[0]);
      setEndDate(meta.delivery_dates[meta.delivery_dates.length - 1]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meta]);

  const ready = !!startDate && !!endDate;

  const metricsState = useApiCall(
    () => ready ? api.metrics(startDate, endDate, horizon) : Promise.reject(new Error("Not ready")),
    [startDate, endDate, horizon, ready]
  );
  const horizonState = useApiCall(
    () => ready ? api.metricsByHorizon(startDate, endDate) : Promise.reject(new Error("Not ready")),
    [startDate, endDate, ready]
  );
  const distState = useApiCall(
    () => ready ? api.errorDistribution(startDate, endDate, horizon) : Promise.reject(new Error("Not ready")),
    [startDate, endDate, horizon, ready]
  );

  const isLoadingM = metricsState.status === "loading" || metricsState.status === "idle";
  const isLoadingH = horizonState.status === "loading" || horizonState.status === "idle";
  const isLoadingD = distState.status === "loading" || distState.status === "idle";
  const m = metricsState.status === "success" ? metricsState.data : null;
  const hData = horizonState.status === "success" ? horizonState.data.data : [];
  const dData = distState.status === "success" ? distState.data.bins : [];

  const metricsError = metricsState.status === "error" ? metricsState.message : null;

  // Build horizon select options: group to common values
  const horizonOptions = [0.5, 1, 2, 4, 6, 8, 10, 12, 16.5, 18, 24, 36, 48];

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex flex-wrap items-end gap-4">
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Start date</label>
          <select
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-600"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          >
            {meta.delivery_dates.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">End date</label>
          <select
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-600"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          >
            {meta.delivery_dates.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">
            Horizon (hours ahead)
          </label>
          <select
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-600"
            value={horizon}
            onChange={(e) => setHorizon(Number(e.target.value))}
          >
            {horizonOptions.map((h) => <option key={h} value={h}>{h}h</option>)}
          </select>
        </div>
      </div>

      {metricsError && (
        <Alert variant="error">Could not load metrics: {metricsError}</Alert>
      )}

      {/* Metric cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <MetricCard
          title="MAE"
          value={fmtMW(m?.mae)}
          caption="Mean absolute error — typical size of the miss."
          loading={isLoadingM}
        />
        <MetricCard
          title="RMSE"
          value={fmtMW(m?.rmse)}
          caption="Root mean square error — penalises large misses more."
          loading={isLoadingM}
        />
        <MetricCard
          title="Bias"
          value={fmtSigned(m?.bias)}
          caption={m ? biasCaptionText(m.bias) : "Mean signed error (+ = over-forecast)."}
          loading={isLoadingM}
        />
        <MetricCard
          title="P90 abs error"
          value={fmtMW(m?.p90_abs_error)}
          caption={`9 in 10 errors fall below this. nMAE: ${fmtPct(m?.normalised_mae)}`}
          loading={isLoadingM}
        />
      </div>

      {m && (
        <p className="text-xs text-slate-400">
          Based on {m.sample_count.toLocaleString()} paired slots at H = {m.horizon_hours}h. Timestamps in UTC.
        </p>
      )}

      {/* Charts */}
      <div className="rounded-xl border border-slate-200 bg-white shadow-sm p-4">
        <div className="flex items-center gap-2 mb-3">
          <h2 className="font-semibold text-slate-700">Actual vs forecast over time</h2>
          <TimezoneBadge />
        </div>
        <ActualVsForecastChart
          data={m?.time_series ?? []}
          loading={isLoadingM}
        />
        <p className="mt-2 text-xs text-slate-400">
          Sampled every 2 hours for readability. Forecast at H = {horizon}h horizon.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm p-4">
          <h2 className="font-semibold text-slate-700 mb-3">MAE by forecast horizon</h2>
          <ErrorByHorizonChart data={hData} loading={isLoadingH} />
          <p className="mt-2 text-xs text-slate-400">
            6-hour buckets. Longer horizons generally show higher error as the forecast becomes less certain.
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white shadow-sm p-4">
          <h2 className="font-semibold text-slate-700 mb-3">
            Error distribution at H = {horizon}h
          </h2>
          <ErrorHistogram bins={dData} loading={isLoadingD} />
          <p className="mt-2 text-xs text-slate-400">
            Positive error = over-forecast. A right-skewed distribution means the model tends to over-predict.
          </p>
        </div>
      </div>
    </div>
  );
}
