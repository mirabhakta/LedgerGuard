import type { DecimalValue } from "../api/types";

const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: "$",
  EUR: "€",
  GBP: "£",
};

export function currencySymbol(currency: string): string {
  return CURRENCY_SYMBOLS[currency.toUpperCase()] ?? `${currency.toUpperCase()} `;
}

/**
 * Formats a decimal amount without floating point drift.
 * The backend serializes Decimal values as strings ("10367.94").
 */
export function formatAmount(value: DecimalValue | null | undefined, currency = "USD"): string {
  if (value === null || value === undefined || value === "") return "—";
  const raw = typeof value === "number" ? value.toFixed(2) : String(value).trim();
  const negative = raw.startsWith("-");
  const [intPart = "0", fracPart = "0"] = raw.replace(/^[+-]/, "").split(".");
  const grouped = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const frac = (fracPart + "00").slice(0, 2);
  return `${negative ? "-" : ""}${currencySymbol(currency)}${grouped}.${frac}`;
}

/** "14:02:11" in UTC. */
export function formatUtcTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}:${pad(date.getUTCSeconds())}`;
}

const MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];

/** "OCT 17 · 14:02 UTC" */
export function formatUtcClock(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${MONTHS[date.getUTCMonth()]} ${date.getUTCDate()} · ${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())} UTC`;
}

/** "2026-10-18 · 01:17 UTC" */
export function formatUtcDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())} · ${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())} UTC`;
}

export function formatLatency(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "—";
  if (ms >= 100) return `${Math.round(ms)} ms`;
  if (ms >= 10) return `${ms.toFixed(1)} ms`;
  return `${ms.toFixed(2)} ms`;
}

export function formatCount(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return String(value).padStart(2, "0");
}

/** Age of an action: "just now", "22 m", "1 h 04 m", "2 d 06 h". */
export function formatAge(fromIso: string, now: number = Date.now()): string {
  const from = new Date(fromIso).getTime();
  if (Number.isNaN(from)) return "—";
  const minutes = Math.max(0, Math.floor((now - from) / 60_000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} m`;
  const hours = Math.floor(minutes / 60);
  const restMinutes = minutes % 60;
  if (hours < 24) return `${hours} h ${String(restMinutes).padStart(2, "0")} m`;
  const days = Math.floor(hours / 24);
  return `${days} d ${String(hours % 24).padStart(2, "0")} h`;
}

export function shortId(value: string | null | undefined, length = 10): string {
  if (!value) return "—";
  return value.length <= length ? value : `${value.slice(0, length)}…`;
}

/** Metric values arrive as numbers inside free-form benchmark metrics. */
export function formatMetricValue(value: DecimalValue | null | undefined, key: string): string {
  if (value === null || value === undefined) return "—";
  const numeric = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(numeric)) return String(value);
  if (key.includes("latency")) {
    return numeric < 1 ? `${numeric.toFixed(2)} ms` : `${Math.round(numeric)} ms`;
  }
  if (Number.isInteger(numeric) && Math.abs(numeric) >= 1000) return String(numeric);
  if (Number.isInteger(numeric) && key.includes("count")) return String(numeric);
  return numeric.toFixed(2);
}

export function formatPercent(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

/** Human-friendly title from a metric key: dangerous_action_prevention_rate -> Dangerous action prevention rate */
export function humanizeKey(key: string): string {
  const text = key.replace(/_/g, " ").trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}
