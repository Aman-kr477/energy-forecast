// src/lib/api.ts
// API_BASE: uses VITE_API_BASE_URL env var if set, otherwise falls back to
// the hardcoded Render URL. In local dev the Vite proxy handles /api/* calls.
import type {
  ActualsResponse,
  ErrorDistributionResponse,
  ForecastResponse,
  MetaResponse,
  MetricsByHorizonResponse,
  MetricsResponse,
} from "@/types/api";

const RENDER_URL = "https://energy-forecast-2z7m.onrender.com";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? RENDER_URL).replace(/\/$/, "");

async function get<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${API_BASE}${path}`);
  if (params) Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  const res = await fetch(url.toString());
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body?.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

const BASE = "/api";

export const api = {
  meta: () => get<MetaResponse>(`${BASE}/meta`),
  actuals: (start: string, end: string) =>
    get<ActualsResponse>(`${BASE}/actuals`, { start, end }),
  forecast: (delivery_date: string, cutoff: string) =>
    get<ForecastResponse>(`${BASE}/forecast`, { delivery_date, cutoff }),
  metrics: (start: string, end: string, horizon: number) =>
    get<MetricsResponse>(`${BASE}/metrics`, { start, end, horizon: String(horizon) }),
  metricsByHorizon: (start: string, end: string) =>
    get<MetricsByHorizonResponse>(`${BASE}/metrics/by-horizon`, { start, end }),
  errorDistribution: (start: string, end: string, horizon: number) =>
    get<ErrorDistributionResponse>(`${BASE}/metrics/error-distribution`, {
      start, end, horizon: String(horizon),
    }),
};