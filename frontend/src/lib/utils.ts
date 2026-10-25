// src/lib/utils.ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { format, parseISO } from "date-fns";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format an ISO UTC string to HH:mm (UTC label shown separately) */
export function fmtTime(iso: string | null): string {
  if (!iso) return "—";
  try { return format(parseISO(iso), "HH:mm"); } catch { return "—"; }
}

/** Format an ISO UTC string to dd MMM HH:mm */
export function fmtDateTime(iso: string | null): string {
  if (!iso) return "—";
  try { return format(parseISO(iso), "dd MMM HH:mm"); } catch { return "—"; }
}

/** Format MW with thousands separator */
export function fmtMW(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${Math.round(v).toLocaleString()} MW`;
}

/** Format MWh */
export function fmtMWh(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${Math.round(v).toLocaleString()} MWh`;
}

/** Format a number with sign for bias/error */
export function fmtSigned(v: number | null | undefined, unit = "MW"): string {
  if (v == null) return "—";
  const sign = v >= 0 ? "+" : "";
  return `${sign}${Math.round(v).toLocaleString()} ${unit}`;
}

/** Percent with 1 dp */
export function fmtPct(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${(v * 100).toFixed(1)}%`;
}

/** Plain-English caption for a bias value */
export function biasCaptionText(bias: number): string {
  const abs = Math.abs(Math.round(bias));
  const dir = bias >= 0 ? "over-forecasts" : "under-forecasts";
  return `Forecasts tend to ${dir} by ~${abs.toLocaleString()} MW on average.`;
}
