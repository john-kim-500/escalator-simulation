// Chart.js charts for experiment results: bars with error bars (compare) and
// lines with a shaded 95% band (sweep). Chart.js is loaded on first use.

import { cssVar } from "./canvas-util.js";
import { ciBounds, withAlpha } from "./experiment-util.js";

export const CHARTJS_VERSION = "4.6.1";
export const CHARTJS_URL = `https://cdn.jsdelivr.net/npm/chart.js@${CHARTJS_VERSION}/dist/chart.umd.min.js`;

let loading = null;

/** Load Chart.js once (a classic script that defines window.Chart). */
export function loadChartJs() {
  if (globalThis.Chart) return Promise.resolve(globalThis.Chart);
  loading ??= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = CHARTJS_URL;
    script.crossOrigin = "anonymous";
    script.onload = () => resolve(globalThis.Chart);
    script.onerror = () => {
      loading = null; // allow a retry
      script.remove();
      reject(new Error("could not load the chart library from cdn.jsdelivr.net"));
    };
    document.head.append(script);
  });
  return loading;
}

/** Draws a vertical error bar on each bar from dataset.errorBars: [[low, high], ...]. */
const errorBarPlugin = {
  id: "errorBars",
  afterDatasetsDraw(chart) {
    const { ctx } = chart;
    chart.data.datasets.forEach((dataset, di) => {
      if (!dataset.errorBars) return;
      const meta = chart.getDatasetMeta(di);
      const scale = chart.scales[meta.yAxisID];
      ctx.save();
      ctx.strokeStyle = cssVar("--text");
      ctx.lineWidth = 1.5;
      meta.data.forEach((bar, i) => {
        const [low, high] = dataset.errorBars[i] ?? [];
        if (low == null || high == null || low === high) return;
        const x = bar.x, y1 = scale.getPixelForValue(low), y2 = scale.getPixelForValue(high);
        const cap = Math.min(8, bar.width / 4);
        ctx.beginPath();
        ctx.moveTo(x, y1); ctx.lineTo(x, y2);
        ctx.moveTo(x - cap, y1); ctx.lineTo(x + cap, y1);
        ctx.moveTo(x - cap, y2); ctx.lineTo(x + cap, y2);
        ctx.stroke();
      });
      ctx.restore();
    });
  },
};

function baseOptions(yTitle) {
  const text = cssVar("--text-muted");
  const grid = cssVar("--grid");
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    color: text,
    interaction: { mode: "nearest", intersect: false },
    plugins: {
      legend: { labels: { color: text, boxWidth: 14 } },
      tooltip: {},
    },
    scales: {
      x: { ticks: { color: text }, grid: { color: grid } },
      y: { beginAtZero: true, title: { display: true, text: yTitle, color: text },
        ticks: { color: text }, grid: { color: grid } },
    },
  };
}

const ciText = (stats, digits) => {
  if (stats?.mean == null) return "–";
  const ci = stats.ci95 == null ? "" : ` ±${stats.ci95.toFixed(digits)}`;
  return `${stats.mean.toFixed(digits)}${ci}`;
};

/**
 * Bar chart of one metric per strategy, with 95% error bars.
 * @param {HTMLCanvasElement} canvas
 * @param {{labels: string[], colors: string[], stats: object[], title: string,
 *   digits?: number}} spec
 */
export function barChart(Chart, canvas, { labels, colors, stats, title, digits = 1 }) {
  const options = baseOptions(title);
  options.plugins.legend.display = false;
  options.plugins.tooltip.callbacks = { label: (item) => ciText(stats[item.dataIndex], digits) };
  options.scales.x.grid.display = false;
  // Leave room above the tallest error bar, and below the lowest one if any go
  // below zero (time saved can be negative).
  const top = Math.max(0, ...stats.map((s) => ciBounds(s)[1] ?? 0));
  const bottom = Math.min(0, ...stats.map((s) => ciBounds(s)[0] ?? 0));
  options.scales.y.suggestedMax = top * 1.08;
  options.scales.y.suggestedMin = bottom * 1.08;
  return new Chart(canvas, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: title,
        data: stats.map((s) => s?.mean ?? null),
        backgroundColor: colors.map((c) => withAlpha(c, 0.75)),
        borderColor: colors,
        borderWidth: 1.5,
        maxBarThickness: 90,
        errorBars: stats.map(ciBounds),
      }],
    },
    options,
    plugins: [errorBarPlugin],
  });
}

/**
 * Line chart of one metric against the swept value, one line per strategy
 * with a shaded band for the 95% margin of error.
 * @param {{xTitle: string, yTitle: string, values: number[],
 *          series: {name: string, color: string, stats: object[]}[], digits?: number}} spec
 */
export function sweepChart(Chart, canvas, { xTitle, yTitle, values, series, digits = 1 }) {
  const datasets = [];
  for (const s of series) {
    const bounds = s.stats.map(ciBounds);
    const point = (i, y) => ({ x: values[i], y });
    datasets.push(
      { label: `${s.name} upper`, band: true, data: bounds.map(([, hi], i) => point(i, hi)),
        borderWidth: 0, pointRadius: 0, pointHitRadius: 0, fill: false },
      { label: `${s.name} lower`, band: true, data: bounds.map(([lo], i) => point(i, lo)),
        borderWidth: 0, pointRadius: 0, pointHitRadius: 0, fill: "-1",
        backgroundColor: withAlpha(s.color, 0.18) },
      { label: s.name, stats: s.stats, data: s.stats.map((st, i) => point(i, st?.mean ?? null)),
        borderColor: s.color, backgroundColor: s.color, borderWidth: 2.5, pointRadius: 3,
        tension: 0, fill: false },
    );
  }
  const options = baseOptions(yTitle);
  options.scales.x.type = "linear";
  options.scales.x.title = { display: true, text: xTitle, color: options.color };
  options.scales.x.min = Math.min(...values);
  options.scales.x.max = Math.max(...values);
  options.scales.x.grid.color = options.scales.y.grid.color;
  options.plugins.legend.labels.filter = (item, data) => !data.datasets[item.datasetIndex].band;
  options.plugins.tooltip.filter = (item) => !item.dataset.band;
  options.plugins.tooltip.callbacks = {
    title: (items) => `${xTitle}: ${items[0]?.parsed.x}`,
    label: (item) => `${item.dataset.label}: ${ciText(item.dataset.stats[item.dataIndex], digits)}`,
  };
  options.interaction = { mode: "index", intersect: false };
  return new Chart(canvas, { type: "line", data: { datasets }, options });
}
