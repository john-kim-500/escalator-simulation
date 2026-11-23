// Experiments view: runs compare/sweep in the worker with progress and cancel,
// then shows the command line's tables, Chart.js charts, downloads and
// "Watch this scenario".

import { el } from "./dom.js";
import { cssVar, onThemeChange } from "./canvas-util.js";
import { formatChange, formatClock } from "./format.js";
import { barChart, loadChartJs, sweepChart } from "./experiment-charts.js";
import { defaultRange, downloadName, etaSeconds, formatEta, formatMeanCi, parseList,
  rangeValues } from "./experiment-util.js";

const SERIES_VARS = ["--series-1", "--series-2", "--series-3"];
const DEFAULT_REPLICATIONS = { compare: 10, sweep: 5 }; // the command line's defaults
const MAX_REPLICATIONS = 200;
const KIND_NOTES = {
  compare: "Runs every strategy on the same crowds (seeds) and averages the results, "
    + "with a 95% margin of error.",
  sweep: "Compares the strategies at each value of one setting, to see where one starts to win.",
};

// Result table columns: [key, header, digits, percent]. Same metrics as the command line.
const METRICS = [
  ["throughput_per_min", "Throughput /min", 1],
  ["wait_mean", "Average wait s", 1],
  ["wait_p95", "95% waited less than s", 1],
  ["trip_mean", "Average trip s", 1],
  ["queue_max", "Longest queue", 0],
  ["queue_end", "Queue at end", 0],
  ["walked_share", "Walked", 0, true],
];

function numberInput(attrs) {
  return el("input", { type: "number", inputmode: "decimal", ...attrs });
}

function labelled(text, input, extra = null) {
  return el("label", { class: "inline-field" }, el("span", { text }), input, extra);
}

export class ExperimentsView {
  /**
   * @param {HTMLElement} root
   * @param {EngineClient} client
   * @param {object} info  the worker's `info` reply
   * @param {object} hooks
   * @param {() => {ok: boolean, config: object|null}} hooks.getSettings  the last check() result
   * @param {(scenario: {config: object, seed: number, strategies: string[]}) => void} hooks.onWatch
   */
  constructor(root, client, info, { getSettings, onWatch }) {
    this.root = root;
    this.client = client;
    this.info = info;
    this.getSettings = getSettings;
    this.onWatch = onWatch;
    this.kind = "compare";
    this.valueMode = "range";
    this.repsTouched = false;
    this.running = false;
    this.charts = [];
    this.last = null; // {spec, result}
    this.render();
    onThemeChange(() => this.last && this.renderCharts());
  }

  // ---------------------------------------------------------------- form

  render() {
    const kindGroup = el("div", { class: "segmented", role: "group", "aria-label": "Experiment type" });
    for (const [kind, label] of [["compare", "Compare"], ["sweep", "Sweep"]]) {
      const b = el("button", { type: "button", text: label, "data-kind": kind });
      b.addEventListener("click", () => this.setKind(kind));
      kindGroup.append(b);
    }
    this.kindGroup = kindGroup;
    this.kindNote = el("p", { class: "card-note" });

    this.strategyBoxes = el("fieldset", { class: "strategies" }, el("legend", { text: "Strategies" }));
    for (const [name, description] of Object.entries(this.info.strategies)) {
      const box = el("input", { type: "checkbox", value: name, checked: true });
      box.addEventListener("change", () => this.updateSummary());
      this.strategyBoxes.append(el("label", { title: description }, box, ` ${name}`));
    }

    this.reps = numberInput({ id: "exp-reps", min: 1, max: MAX_REPLICATIONS, step: 1,
      value: DEFAULT_REPLICATIONS.compare, inputmode: "numeric" });
    this.reps.addEventListener("input", () => { this.repsTouched = true; this.updateSummary(); });
    this.seed = numberInput({ id: "exp-seed", min: 0, step: 1, value: 1, inputmode: "numeric" });
    this.seed.addEventListener("input", () => this.updateSummary());

    // Sweep settings.
    this.param = el("select", { id: "exp-param" });
    for (const [name, p] of Object.entries(this.info.param_info)) {
      this.param.append(el("option", { value: name, text: `${p.label} (${name})` }));
    }
    this.param.value = "walk_fraction";
    this.param.addEventListener("change", () => { this.resetRange(); this.updateSummary(); });

    const modeGroup = el("div", { class: "segmented", role: "group", "aria-label": "How to enter values" });
    for (const [mode, label] of [["range", "Range"], ["list", "List"]]) {
      const b = el("button", { type: "button", text: label, "data-mode": mode });
      b.addEventListener("click", () => this.setValueMode(mode));
      modeGroup.append(b);
    }
    this.modeGroup = modeGroup;
    this.from = numberInput({ id: "exp-from", "aria-label": "From" });
    this.to = numberInput({ id: "exp-to", "aria-label": "To" });
    this.step = numberInput({ id: "exp-step", "aria-label": "Step", min: 0 });
    this.list = el("input", { type: "text", id: "exp-list", placeholder: "e.g. 0, 0.1, 0.25, 0.5",
      "aria-label": "Values, separated by commas", spellcheck: "false" });
    for (const input of [this.from, this.to, this.step, this.list]) {
      input.addEventListener("input", () => this.updateSummary());
    }
    this.rangeRow = el("div", { class: "control-row" },
      labelled("From", this.from), labelled("To", this.to), labelled("Step", this.step));
    this.listRow = el("div", { class: "control-row" }, this.list);
    this.preview = el("p", { class: "values-preview" });
    this.sweepBox = el("div", { class: "sweep-settings" },
      el("div", { class: "control-row" }, labelled("Setting to vary", this.param), modeGroup),
      this.rangeRow, this.listRow, this.preview);

    this.summary = el("p", { class: "card-note exp-summary" });
    this.messages = el("div", { class: "messages", "aria-live": "polite" }); // form problems
    this.runError = el("p", { class: "message error", role: "alert", hidden: true }); // last run failed

    this.runButton = el("button", { type: "button", class: "button primary", text: "Run" });
    this.runButton.addEventListener("click", () => this.run());
    this.cancelButton = el("button", { type: "button", class: "button", text: "Cancel", hidden: true });
    this.cancelButton.addEventListener("click", () => this.cancel());
    this.progress = el("progress", { max: 1, value: 0, "aria-label": "Experiment progress", hidden: true });
    this.progressText = el("span", { class: "progress-text", role: "status" });

    const form = el("section", { class: "card exp-form", "aria-labelledby": "exp-title" },
      el("div", { class: "control-row" }, el("h2", { class: "card-title", id: "exp-title", text: "Experiment" }), kindGroup),
      this.kindNote,
      el("div", { class: "control-row" }, this.strategyBoxes),
      el("div", { class: "control-row" },
        labelled("Replications", this.reps), labelled("First seed", this.seed)),
      this.sweepBox,
      this.summary,
      this.messages,
      this.runError,
      el("div", { class: "control-row" }, this.runButton, this.cancelButton, this.progress, this.progressText));

    this.results = el("section", { class: "card results", hidden: true, "aria-live": "polite" });
    this.root.replaceChildren(form, this.results);
    this.resetRange();
    this.setKind("compare");
    this.setValueMode("range");
  }

  setKind(kind) {
    this.kind = kind;
    this.kindGroup.querySelectorAll("button").forEach((b) =>
      b.setAttribute("aria-pressed", String(b.dataset.kind === kind)));
    this.kindNote.textContent = KIND_NOTES[kind];
    this.sweepBox.hidden = kind !== "sweep";
    if (!this.repsTouched) this.reps.value = DEFAULT_REPLICATIONS[kind];
    this.updateSummary();
  }

  setValueMode(mode) {
    // Switching to a list starts it from the current range.
    const fromRange = mode === "list" && this.valueMode === "range" ? this.sweepValues().values : null;
    this.valueMode = mode;
    this.modeGroup.querySelectorAll("button").forEach((b) =>
      b.setAttribute("aria-pressed", String(b.dataset.mode === mode)));
    this.rangeRow.hidden = mode !== "range";
    this.listRow.hidden = mode !== "list";
    if (fromRange?.length && !this.list.value.trim()) this.list.value = fromRange.join(", ");
    this.updateSummary();
  }

  resetRange() {
    const p = this.info.param_info[this.param.value];
    const r = defaultRange(p);
    for (const input of [this.from, this.to, this.step]) {
      input.min = p.min;
      input.max = p.max;
      input.step = p.step;
    }
    this.step.min = p.step;
    this.from.value = r.from;
    this.to.value = r.to;
    this.step.value = r.step;
    this.list.value = "";
  }

  sweepValues() {
    if (this.valueMode === "list") return parseList(this.list.value);
    return rangeValues(Number(this.from.value), Number(this.to.value), Number(this.step.value));
  }

  /** Called by the app whenever the settings panel was checked. */
  settingsChanged() {
    this.updateSummary();
  }

  /** The experiment the form describes, or {error}. */
  buildSpec() {
    const settings = this.getSettings();
    if (!settings?.ok) return { error: "Fix the settings on the left first." };
    const strategies = [...this.strategyBoxes.querySelectorAll("input:checked")].map((b) => b.value);
    if (!strategies.length) return { error: "Choose at least one strategy." };
    const replications = Number(this.reps.value);
    if (!Number.isInteger(replications) || replications < 1 || replications > MAX_REPLICATIONS) {
      return { error: `Replications must be a whole number from 1 to ${MAX_REPLICATIONS}.` };
    }
    const seed = Number(this.seed.value);
    if (!Number.isInteger(seed) || seed < 0) return { error: "The first seed must be a whole number, 0 or more." };
    const spec = { kind: this.kind, config: settings.config, strategies, replications, seed };
    if (this.kind === "sweep") {
      const { values, error } = this.sweepValues();
      if (error) return { error: `Values: ${error}.` };
      spec.param = this.param.value;
      spec.values = values;
    }
    return { spec };
  }

  updateSummary() {
    const { spec, error } = this.buildSpec();
    if (this.kind === "sweep") {
      const { values, error: valueError } = this.sweepValues();
      this.preview.textContent = valueError
        ? "" : `${values.length} value${values.length === 1 ? "" : "s"}: ${values.join(", ")}`;
    }
    this.messages.replaceChildren(...(error ? [el("p", { class: "message error", text: error })] : []));
    this.runButton.disabled = Boolean(error) || this.running;
    if (!spec) {
      this.summary.textContent = "";
      return;
    }
    const points = spec.kind === "sweep" ? spec.values.length : 1;
    const runs = points * spec.strategies.length * spec.replications;
    const seeds = spec.replications === 1 ? `seed ${spec.seed}` : `seeds ${spec.seed}–${spec.seed + spec.replications - 1}`;
    let text = `${runs} run${runs === 1 ? "" : "s"}: `
      + (spec.kind === "sweep" ? `${points} value${points === 1 ? "" : "s"} × ` : "")
      + `${spec.strategies.length} strateg${spec.strategies.length === 1 ? "y" : "ies"} × `
      + `${spec.replications} replication${spec.replications === 1 ? "" : "s"} (${seeds}), `
      + `each ${formatClock(spec.config.duration)} long, using the settings on the left.`;
    if (spec.kind === "sweep") {
      text += ` The swept values replace ${spec.param} = ${spec.config[spec.param]}.`;
    }
    this.summary.textContent = text;
  }

  // -------------------------------------------------------------- running

  async run() {
    const { spec, error } = this.buildSpec();
    if (error || this.running) return;
    this.running = true;
    this.runButton.disabled = true;
    this.cancelButton.hidden = false;
    this.cancelButton.disabled = false;
    this.progress.hidden = false;
    this.progress.value = 0;
    this.progressText.textContent = "Starting…";
    this.runError.hidden = true;
    const started = performance.now();
    try {
      const out = await this.client.request("exp.run", { spec }, ({ done, total }) => {
        this.progress.value = total ? done / total : 0;
        const eta = etaSeconds((performance.now() - started) / 1000, done, total);
        this.progressText.textContent = `${done} of ${total} runs · ${formatEta(eta)}`;
      });
      if (out.cancelled) {
        this.progressText.textContent = "Cancelled.";
      } else {
        const seconds = (performance.now() - started) / 1000;
        this.progressText.textContent = `Finished in ${seconds < 10 ? seconds.toFixed(1) : Math.round(seconds)} s.`;
        this.last = { spec, result: out.result };
        this.showResults();
      }
    } catch (err) {
      this.progressText.textContent = "";
      this.runError.textContent = `Could not run: ${err.message}`;
      this.runError.hidden = false;
    } finally {
      this.running = false;
      this.cancelButton.hidden = true;
      this.progress.hidden = true;
      this.updateSummary();
    }
  }

  cancel() {
    this.cancelButton.disabled = true;
    this.progressText.textContent = "Cancelling…";
    this.client.request("exp.cancel").catch(() => {});
  }

  // -------------------------------------------------------------- results

  showResults() {
    const { spec, result } = this.last;
    const { data } = result;
    const config = data.config;
    const seeds = data.seeds.length === 1 ? `seed ${data.seeds[0]}` : `seeds ${data.seeds[0]}–${data.seeds.at(-1)}`;
    const measured = formatClock(config.duration - config.warmup);

    const downloads = el("div", { class: "control-row downloads" },
      this.downloadButton("Download CSV", result.csv, downloadName(data, "csv"), "text/csv"),
      this.downloadButton("Download JSON", result.json, downloadName(data, "json"), "application/json"));
    const note = el("p", { class: "card-note",
      text: `${data.seeds.length} replication${data.seeds.length === 1 ? "" : "s"} per strategy (${seeds}). `
        + `Each run is measured over the ${measured} after a ${formatClock(config.warmup)} warm-up. `
        + "Values are the mean ± the 95% margin of error. The files are the same as the command line's --output csv/json." });

    const warnings = [];
    const runs = data.points
      ? data.points.flatMap((p) => Object.values(p.strategies).flatMap((s) => s.runs))
      : Object.values(data.strategies).flatMap((s) => s.runs);
    if (runs.some((r) => r.warmup_too_short)) {
      warnings.push(el("p", { class: "message warning",
        text: "The warm-up is shorter than one ride, so throughput is underestimated. Raise the warm-up." }));
    }

    this.chartBox = el("div", { class: "exp-charts" });
    const body = data.points ? this.sweepResults(spec, result) : this.compareResults(spec, result);
    this.results.replaceChildren(
      el("h2", { class: "card-title", text: data.points
        ? `Sweep results: ${this.info.param_info[data.param].label}` : "Compare results" }),
      note, ...warnings, ...body, this.chartBox, downloads);
    this.results.hidden = false;
    this.renderCharts();
  }

  compareResults(spec, { data, winners }) {
    const names = Object.keys(data.strategies);
    const summaries = names.map((n) => data.strategies[n].summary);
    const head = el("tr", {}, el("th", { scope: "col", text: "Strategy" }),
      ...METRICS.map(([, h]) => el("th", { scope: "col", text: h })));
    const rows = names.map((name, i) => el("tr", {},
      el("th", { scope: "row" }, this.swatch(i), name),
      ...METRICS.map(([key, , digits, pct]) => el("td", { text: formatMeanCi(summaries[i][key], digits, pct) }))));
    const lines = [];
    if (names.length >= 2) {
      const base = names.includes("walk-left") ? "walk-left" : names[0];
      for (const name of names.filter((n) => n !== base)) {
        const a = data.strategies[name].summary, b = data.strategies[base].summary;
        lines.push(`${name} vs ${base}: throughput ${formatChange(a.throughput_per_min.mean, b.throughput_per_min.mean)}, `
          + `average wait ${formatChange(a.wait_mean.mean, b.wait_mean.mean)}.`);
      }
      lines.push(winners[0] === "tie"
        ? "Most throughput: a tie. The difference is within the margins of error; more replications may separate them."
        : `Most throughput: ${winners[0]}, by more than the margins of error.`);
    }
    const watch = el("button", { type: "button", class: "button", text: "Watch this scenario",
      title: `Open the live view with these settings and seed ${data.seeds[0]}` });
    watch.addEventListener("click", () => this.onWatch({ config: data.config, seed: data.seeds[0], strategies: names }));
    return [
      el("div", { class: "table-wrap" }, el("table", {}, el("thead", {}, head), el("tbody", {}, ...rows))),
      el("div", { class: "verdict" }, ...lines.map((t) => el("p", { text: t }))),
      el("div", { class: "control-row" }, watch),
    ];
  }

  sweepResults(spec, { data, winners }) {
    const names = spec.strategies;
    const head = el("tr", {}, el("th", { scope: "col", text: data.param }),
      ...names.map((n) => el("th", { scope: "col", text: `${n} thru/min` })),
      ...names.map((n) => el("th", { scope: "col", text: `${n} wait s` })),
      el("th", { scope: "col", text: "Most throughput" }),
      el("th", { scope: "col", text: "" }));
    const rows = data.points.map((point, i) => {
      const watch = el("button", { type: "button", class: "button small", text: "Watch",
        "aria-label": `Watch ${data.param} = ${point.value} in the live view` });
      watch.addEventListener("click", () => this.onWatch({
        config: { ...data.config, [data.param]: point.value }, seed: data.seeds[0], strategies: names }));
      return el("tr", {},
        el("th", { scope: "row", text: String(point.value) }),
        ...names.map((n) => el("td", { text: formatMeanCi(point.strategies[n].summary.throughput_per_min) })),
        ...names.map((n) => el("td", { text: formatMeanCi(point.strategies[n].summary.wait_mean) })),
        el("td", { class: winners[i] === "tie" ? "tie" : "winner", text: winners[i] }),
        el("td", {}, watch));
    });
    return [
      el("div", { class: "table-wrap" }, el("table", {}, el("thead", {}, head), el("tbody", {}, ...rows))),
      el("p", { class: "card-note",
        text: "“tie” means the lead is within the margins of error (the command line's rule)." }),
    ];
  }

  swatch(i) {
    return el("span", { class: "swatch", style: `background: var(${SERIES_VARS[i % SERIES_VARS.length]})`,
      "aria-hidden": "true" });
  }

  downloadButton(label, text, filename, type) {
    const b = el("button", { type: "button", class: "button", text: label });
    b.addEventListener("click", () => {
      const url = URL.createObjectURL(new Blob([text], { type }));
      const a = el("a", { href: url, download: filename });
      document.body.append(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
    return b;
  }

  // --------------------------------------------------------------- charts

  async renderCharts() {
    if (!this.last || !this.chartBox) return;
    const { spec, result } = this.last;
    const box = this.chartBox;
    let Chart;
    try {
      Chart = await loadChartJs();
    } catch (err) {
      box.replaceChildren(el("p", { class: "message warning", text: `Charts unavailable: ${err.message}. The table above has every number.` }));
      return;
    }
    if (box !== this.chartBox) return; // newer results arrived meanwhile
    this.charts.forEach((c) => c.destroy());
    this.charts = [];
    const names = spec.strategies;
    const colors = names.map((_, i) => cssVar(SERIES_VARS[i % SERIES_VARS.length]));
    const make = (title) => {
      const canvas = el("canvas", { role: "img", "aria-label": title });
      return { canvas, figure: el("figure", { class: "exp-chart" },
        el("figcaption", { text: title }), el("div", { class: "chart-frame" }, canvas)) };
    };
    const metrics = [["throughput_per_min", "Throughput (people/min)"], ["wait_mean", "Average wait (s)"]];
    const figures = metrics.map(([, title]) => make(title));
    box.replaceChildren(...figures.map((f) => f.figure));

    const { data } = result;
    metrics.forEach(([key, title], i) => {
      const canvas = figures[i].canvas;
      if (data.points) {
        const label = this.info.param_info[data.param];
        this.charts.push(sweepChart(Chart, canvas, {
          xTitle: `${label.label}${label.unit ? ` (${label.unit})` : ""}`,
          yTitle: title,
          values: data.points.map((p) => p.value),
          series: names.map((n, j) => ({ name: n, color: colors[j],
            stats: data.points.map((p) => p.strategies[n].summary[key]) })),
        }));
      } else {
        this.charts.push(barChart(Chart, canvas, {
          labels: names, colors, title,
          stats: names.map((n) => data.strategies[n].summary[key]),
        }));
      }
    });
  }
}
