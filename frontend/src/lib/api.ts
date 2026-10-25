// src/lib/api.ts
// Typed fetch wrappers — all business logic stays in the backend.
//
// In production (Vercel), VITE_API_BASE_URL must be set to the Heroku backend URL,
// e.g. https://your-app.herokuapp.com
// In local dev, requests go to /api and are proxied by Vite to localhost:8000.
import type {
  ActualsResponse,
  ErrorDistributionResponse,
  ForecastResponse,
  MetaResponse,
  MetricsByHorizonResponse,
  MetricsResponse,
} from "@/types/api";

// Empty string = same-origin (dev proxy). Set VITE_API_BASE_URL for production.
const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

async function get<T>(path: string, params?: Record<string, string>): Promise<T> {
  const fullPath = `${API_BASE}${path}`;
  const url = new URL(fullPath, fullPath.startsWith("http") ? undefined : window.location.origin);
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
    get<MetricsResponse>(`${BASE}/metrics`, {
      start,
      end,
      horizon: String(horizon),
    }),

  metricsByHorizon: (start: string, end: string) =>
    get<MetricsByHorizonResponse>(`${BASE}/metrics/by-horizon`, { start, end }),

  errorDistribution: (start: string, end: string, horizon: number) =>
    get<ErrorDistributionResponse>(`${BASE}/metrics/error-distribution`, {
      start,
      end,
      horizon: String(horizon),
    }),
};