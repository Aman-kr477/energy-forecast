// src/types/api.ts
// Shared types matching the backend Pydantic schemas exactly.

export interface HealthResponse {
  status: string;
}

export interface MetaResponse {
  delivery_dates: string[];
  available_horizons: number[];
  default_cutoff: string;
  timezone: string;
}

export interface ActualPoint {
  start_time: string;
  generation_mw: number;
}

export interface ActualsResponse {
  data: ActualPoint[];
}

export interface ForecastSlot {
  start_time: string;
  forecast_mw: number | null;
  publish_time: string | null;
  horizon_hours: number | null;
  actual_mw: number | null;
  error_mw: number | null;
}

export interface ForecastSummary {
  total_forecast_mwh: number | null;
  peak_forecast_mw: number | null;
  peak_forecast_time: string | null;
  min_forecast_mw: number | null;
  min_forecast_time: string | null;
  earliest_publish_time: string | null;
  latest_publish_time: string | null;
}

export interface ErrorBand {
  p10_mw: number | null;
  p90_mw: number | null;
  based_on_days: number;
}

export interface ForecastResponse {
  delivery_date: string;
  cutoff: string;
  slots: ForecastSlot[];
  summary: ForecastSummary;
  error_band: ErrorBand;
}

export interface TimeSeriesPoint {
  start_time: string;
  actual_mw: number | null;
  forecast_mw: number | null;
  error_mw: number | null;
}

export interface MetricsResponse {
  mae: number;
  rmse: number;
  bias: number;
  p90_abs_error: number;
  normalised_mae: number;
  sample_count: number;
  horizon_hours: number;
  time_series: TimeSeriesPoint[];
}

export interface HorizonMetric {
  horizon_hours: number;
  mae: number;
  rmse: number;
  bias: number;
  sample_count: number;
}

export interface MetricsByHorizonResponse {
  data: HorizonMetric[];
}

export interface HistogramBin {
  bin_left: number;
  bin_right: number;
  count: number;
}

export interface ErrorDistributionResponse {
  horizon_hours: number;
  bins: HistogramBin[];
  sample_count: number;
}
