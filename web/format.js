// Small pure helpers for formatting and chart scales (unit-tested with node --test).

export function formatNumber(value, digits = 1) {
  return value == null || !Number.isFinite(value) ? "–" : value.toFixed(digits);
}

export function formatPercent(value) {
  return value == null || !Number.isFinite(value) ? "–" : `${Math.round(value * 100)}%`;
}

/** 192.4 -> "3:12" */
export function formatClock(seconds) {
  const s = Math.max(0, Math.floor(seconds + 1e-9));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

/** Relative change of a vs b, e.g. "+12.0%"; "–" if b is 0 or missing. */
export function formatChange(a, b) {
  if (a == null || b == null || !b) return "–";
  const change = (a - b) / Math.abs(b);
  return `${change >= 0 ? "+" : "−"}${Math.abs(change * 100).toFixed(1)}%`;
}

/** A "nice" axis step (1, 2 or 5 × 10^k) so that max/step is about `count`. */
export function niceStep(max, count = 5) {
  if (!(max > 0)) return 1;
  const raw = max / count;
  const pow = 10 ** Math.floor(Math.log10(raw));
  const n = raw / pow;
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * pow;
}

/** Axis step for time in seconds, using clock-friendly intervals. */
export function niceTimeStep(maxSeconds, count = 6) {
  const steps = [5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600];
  return steps.find((s) => maxSeconds / s <= count) ?? steps[steps.length - 1];
}

/** Round a value to the number of decimals implied by a slider step. */
export function roundToStep(value, step) {
  const decimals = Math.max(0, -Math.floor(Math.log10(step) + 1e-9));
  return Number(value.toFixed(Math.min(decimals + 1, 6)));
}
