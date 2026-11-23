// Pure helpers for the experiments view (unit-tested with node --test).

import { niceStep, roundToStep } from "./format.js";

export const MAX_SWEEP_VALUES = 50;

/** Values from..to (inclusive) in steps of `step`, without float noise. */
export function rangeValues(from, to, step, maxCount = MAX_SWEEP_VALUES) {
  if (![from, to, step].every(Number.isFinite)) {
    return { values: [], error: "from, to and step must be numbers" };
  }
  if (step <= 0) return { values: [], error: "step must be greater than 0" };
  if (to < from) return { values: [], error: "“to” must not be less than “from”" };
  const count = Math.floor((to - from) / step + 1e-9) + 1;
  if (count > maxCount) {
    return { values: [], error: `that is ${count} values; the limit is ${maxCount}` };
  }
  const values = [];
  for (let i = 0; i < count; i++) values.push(roundToStep(from + i * step, step));
  return { values, error: null };
}

/** "0, 0.1, 0.25" -> [0, 0.1, 0.25]. Commas or spaces separate values. */
export function parseList(text, maxCount = MAX_SWEEP_VALUES) {
  const parts = String(text).split(/[\s,;]+/).filter(Boolean);
  if (!parts.length) return { values: [], error: "enter at least one value" };
  const values = parts.map(Number);
  const bad = parts.find((p, i) => !Number.isFinite(values[i]));
  if (bad !== undefined) return { values: [], error: `“${bad}” is not a number` };
  if (values.length > maxCount) {
    return { values: [], error: `that is ${values.length} values; the limit is ${maxCount}` };
  }
  return { values, error: null };
}

/** A sensible starting range for a parameter, from its slider limits. */
export function defaultRange(param) {
  const span = param.max - param.min;
  let step = Math.max(param.step, niceStep(span, 5));
  if (param.step >= 1) step = Math.max(1, Math.round(step));
  const last = roundToStep(param.min + step * Math.floor(span / step + 1e-9), param.step);
  return { from: param.min, to: last, step };
}

/** Seconds left, from the time taken so far. null until there is something to go on. */
export function etaSeconds(elapsedSeconds, done, total) {
  if (!(done > 0) || done >= total) return done >= total ? 0 : null;
  return (elapsedSeconds / done) * (total - done);
}

/** "about 40 s left", "about 3 min left". */
export function formatEta(seconds) {
  if (seconds == null) return "estimating time left…";
  if (seconds < 1) return "almost done";
  if (seconds < 90) return `about ${Math.max(1, Math.round(seconds / 5) * 5 || 1)} s left`;
  return `about ${Math.round(seconds / 60)} min left`;
}

/** "112.3 ±1.4" in the command line's style (no ± for percentages or single runs). */
export function formatMeanCi(stats, digits = 1, percent = false) {
  if (!stats || stats.mean == null) return "–";
  if (percent) return `${Math.round(stats.mean * 100)}%`;
  const text = stats.mean.toFixed(digits);
  return stats.ci95 == null ? text : `${text} ±${stats.ci95.toFixed(digits)}`;
}

/** Lower/upper bounds of a mean ± CI (the mean itself when there is no CI). */
export function ciBounds(stats) {
  if (!stats || stats.mean == null) return [null, null];
  const ci = stats.ci95 ?? 0;
  return [stats.mean - ci, stats.mean + ci];
}

/** File name for a download, e.g. "sweep-walk_fraction-seed1.csv". */
export function downloadName(data, ext) {
  const seed = data.seeds?.[0] ?? 1;
  return data.points ? `sweep-${data.param}-seed${seed}.${ext}` : `compare-seed${seed}.${ext}`;
}

/** "#0b5cad" or "#abc" or "rgb(…)" with an alpha, as rgba(); unknown formats pass through. */
export function withAlpha(color, alpha) {
  const c = String(color).trim();
  let m = c.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (m) {
    let hex = m[1];
    if (hex.length === 3) hex = [...hex].map((ch) => ch + ch).join("");
    const n = parseInt(hex, 16);
    return `rgba(${n >> 16}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
  }
  m = c.match(/^rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)/i);
  if (m) return `rgba(${m[1]}, ${m[2]}, ${m[3]}, ${alpha})`;
  return c;
}

// ------------------------------------------------------------ time saved
// Wording matches the command line (cli.py `_saving`, `_time_saved_lines`).

/** Shown instead of time saved when the runs didn't finish the line. */
export const DRAIN_HINT = "Set “Finish the line” to 1 to measure time saved for walkers.";

/** Explains who "walkers" are, under tables that split trips by group. */
export const WALKERS_NOTE =
  "Walkers = people who want to walk, counted the same way under every strategy.";

/** "walkers save 41.7 ±7.4 s" or "others lose 10.2 ±5.1 s"; "walkers -" without data. */
export function formatSaving(group, stats) {
  if (!stats || stats.mean == null) return `${group} -`;
  const verb = stats.mean >= 0 ? "save" : "lose";
  const ci = stats.ci95 == null ? "" : ` ±${stats.ci95.toFixed(1)}`;
  return `${group} ${verb} ${Math.abs(stats.mean).toFixed(1)}${ci} s`;
}

/** "walk-left vs stand-both: walkers save … per trip; others lose …" for a time_saved entry. */
export function timeSavedLine(entry) {
  return `${entry.by} vs ${entry.over}: ${formatSaving("walkers", entry.cares)} per trip; `
    + formatSaving("others", entry.others);
}

/**
 * A time_saved-style entry from two live results (one crowd, so no margin):
 * the saving is the first result's trip minus the second's, like the pairs
 * the experiments make.
 */
export function liveTimeSaved([over, by]) {
  const diff = (key) => (over[key] == null || by[key] == null
    ? { mean: null, ci95: null } : { mean: over[key] - by[key], ci95: null });
  return { by: by.strategy, over: over.strategy, drained: Boolean(over.drained && by.drained),
    cares: diff("trip_mean_cares"), others: diff("trip_mean_others") };
}
