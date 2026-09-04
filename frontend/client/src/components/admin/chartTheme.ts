/**
 * Chart tokens for the admin dashboard.
 *
 * Severity is a *status* vocabulary (critical / warning / info) — reserved,
 * never reused as a series color, and always shipped beside a label. Push vs
 * pull-request is a *categorical* pair (blue / aqua) validated for the dark
 * surface these charts render on (#13151b).
 */

export const SURFACE = "#13151b";      // card the charts sit on
export const SURFACE_SUNK = "#0f1117"; // inset wells
export const GRID = "#22252f";         // hairline gridline, one step off surface
export const AXIS = "#2f3341";

export const INK = {
  primary: "#f4f4f5",
  secondary: "#a1a1aa",
  muted: "#71717a",
};

/** Status palette — fixed, documented as ≥3:1 on a dark surface. */
export const SEVERITY = {
  error: "#d03b3b",
  warning: "#fab219",
  notice: "#3987e5",
} as const;

/** Categorical slots 1 and 3 — validated pair (ΔE 20.9 normal, 19.6 deutan). */
export const EVENT = {
  push: "#3987e5",
  pull_request: "#199e70",
  scan: "#9085e9",
} as const;

export type SeverityKey = keyof typeof SEVERITY;

export const SEVERITY_LABEL: Record<SeverityKey, string> = {
  error: "Confirmed leak",
  warning: "Exception risk",
  notice: "Notice",
};

/** 1,284 → "1,284"; 12,900 → "12.9K" */
export function compact(n: number): string {
  if (n < 1000) return String(n);
  if (n < 1_000_000) return `${(n / 1000).toFixed(n < 10_000 ? 1 : 0)}K`;
  return `${(n / 1_000_000).toFixed(1)}M`;
}

/** Shared axis props so every chart wears the same recessive chrome. */
export const axisProps = {
  stroke: AXIS,
  tick: { fill: INK.muted, fontSize: 11 },
  tickLine: false,
  axisLine: { stroke: AXIS },
} as const;
