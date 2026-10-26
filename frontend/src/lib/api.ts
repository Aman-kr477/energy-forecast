// src/lib/api.ts
// In production: VITE_API_BASE_URL points to the Render backend.
// In local dev: empty string uses the Vite proxy to localhost:8000.
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
  const fullUrl = API_BASE
    ? `${API_BASE}${path}`
    : path;
  const url = new URL(fullUrl, window.location.origin);
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