// src/features/decision/DecisionScreen.tsx
// Screen 1: "Forecast for decision"
// Date picker + cutoff selector → line chart with error band + summary cards + reveal actuals toggle.
import { useEffect } from "react";
import { api } from "@/lib/api";
import { useApiCall } from "@/hooks/useApi";
import { useDecisionStore } from "@/store/filterStore";
import { ForecastChart } from "@/components/charts/ForecastChart";
import { MetricCard } from "@/components/common/MetricCard";
import { Alert } from "@/components/ui/alert";
import { TimezoneBadge } from "@/components/common/TimezoneBadge";
import { fmtMW, fmtMWh, fmtDateTime } from "@/lib/utils";
import type { MetaResponse } from "@/types/api";

const CUTOFF_OPTIONS = [
  "06:00","07:00","08:00","09:00","10:00","11:00","12:00",
];

interface Props { meta: MetaResponse }

export function DecisionScreen({ meta }: Props) {
  const { deliveryDate, cutoff, showActuals, setDeliveryDate, setCutoff, setShowActuals } =
    useDecisionStore();

  // Default to first available date
  useEffect(() => {
    if (!deliveryDate && meta.delivery_dates.length) {
      setDeliveryDate(meta.delivery_dates[0]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meta]);

  const forecastState = useApiCall(
    () => api.forecast(deliveryDate, cutoff),
    [deliveryDate, cutoff]
  );

  const isLoading = forecastState.status === "loading" || forecastState.status === "idle";
  const isError = forecastState.status === "error";
  const data = forecastState.status === "success" ? forecastState.data : null;
  const s = data?.summary;

  const biasNote =
    data?.error_band.p10_mw != null
      ? `Error band from ${data.error_band.based_on_days} prior day(s). P10: ${Math.round(data.error_band.p10_mw).toLocaleString()} MW, P90: ${Math.round(data.error_band.p90_mw!).toLocaleString()} MW.`
      : "No historical error band available for this date (insufficient prior days).";

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex flex-wrap items-end gap-4">
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">
            Delivery date
          </label>
          <select
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-600"
            value={deliveryDate}
            onChange={(e) => setDeliveryDate(e.target.value)}
          >
            {meta.delivery_dates.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">
            Decision cutoff <span className="text-slate-400">(Europe/London)</span>
          </label>
          <select
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-600"
            value={cutoff}
            onChange={(e) => setCutoff(e.target.value)}
          >
            {CUTOFF_OPTIONS.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2 pb-0.5">
          <button
            onClick={() => setShowActuals(!showActuals)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-600 ${showActuals ? "bg-brand-600" : "bg-slate-300"}`}
            aria-pressed={showActuals}
            aria-label="Reveal actuals"
          >
            <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${showActuals ? "translate-x-6" : "translate-x-1"}`} />
          </button>
          <span className="text-sm font-medium text-slate-700">Reveal actuals</span>
        </div>
      </div>

      {/* Error state */}
      {isError && (
        <Alert variant="error">
          Failed to load forecast: {(forecastState as { status: "error"; message: string }).message}
        </Alert>
      )}

      {/* Chart */}
      <div className="rounded-xl border border-slate-200 bg-white shadow-sm p-4">
        <div className="flex items-center gap-2 mb-3">
          <h2 className="font-semibold text-slate-700">Wind generation forecast</h2>
          <TimezoneBadge />
        </div>
        <ForecastChart
          slots={data?.slots ?? []}
          errorBand={data?.error_band ?? { p10_mw: null, p90_mw: null, based_on_days: 0 }}
          showActuals={showActuals}
          loading={isLoading}
        />
        <p className="mt-2 text-xs text-slate-400">{biasNote}</p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <MetricCard
          title="Total forecast"
          value={fmtMWh(s?.total_forecast_mwh)}
          caption="Sum of all 30-min periods × 0.5 h"
          loading={isLoading}
        />
        <MetricCard
          title="Peak forecast"
          value={fmtMW(s?.peak_forecast_mw)}
          caption={s?.peak_forecast_time ? `At ${fmtDateTime(s.peak_forecast_time)} UTC` : "—"}
          loading={isLoading}
        />
        <MetricCard
          title="Minimum forecast"
          value={fmtMW(s?.min_forecast_mw)}
          caption={s?.min_forecast_time ? `At ${fmtDateTime(s.min_forecast_time)} UTC` : "—"}
          loading={isLoading}
        />
        <MetricCard
          title="Forecast published"
          value={isLoading ? "—" : (s?.latest_publish_time ? fmtDateTime(s.latest_publish_time) + " UTC" : "No data")}
          caption={
            s?.earliest_publish_time !== s?.latest_publish_time
              ? `Earliest: ${fmtDateTime(s?.earliest_publish_time ?? null)}`
              : "Single snapshot used for all slots"
          }
          loading={isLoading}
        />
      </div>
    </div>
  );
}

