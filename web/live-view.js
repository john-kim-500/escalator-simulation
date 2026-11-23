// Live view: runs every selected strategy on the same crowd in lockstep and
// animates them side by side, with live numbers, a chart and final results.

import { EscalatorCanvas, KIND_SHAPES, drawShape } from "./escalator-canvas.js";
import { LiveChart } from "./live-chart.js";
import { cssVar, onThemeChange } from "./canvas-util.js";
import { formatChange, formatClock, formatNumber, formatPercent } from "./format.js";
import { el } from "./dom.js";
import { DRAIN_HINT, WALKERS_NOTE, liveTimeSaved, timeSavedLine } from "./experiment-util.js";

const SPEEDS = [1, 2, 5, 10, 25, 50];
const DEFAULT_SPEED = 10;
const MAX_QUEUE = 80;          // queueing people per lane sent with each snapshot
const MAX_FRAME_SECONDS = 0.25; // ignore longer gaps (e.g. a background tab)
const HISTORY_EVERY = 1.0;      // simulated seconds between chart points
const SERIES_VARS = ["--series-1", "--series-2", "--series-3"];

export class LiveView {
  constructor(root, client, info) {
    this.root = root;
    this.client = client;
    this.info = info;
    this.strategies = Object.keys(info.strategies);
    this.seed = 1;
    this.speed = DEFAULT_SPEED;
    this.playing = true;
    this.active = true; // false while another view is showing
    this.values = null;
    this.state = null;
    this.generation = 0;
    this.busy = false;
    this.owed = 0;
    this.lastFrame = null;
    this.onStrategiesChange = () => {};
    this.render();
    onThemeChange(() => {
      this.renderLegend();
      this.redraw();
    });
    requestAnimationFrame((t) => this.tick(t));
    document.addEventListener("keydown", (e) => {
      const typing = e.target.closest?.("input, select, textarea, button");
      if (e.code === "Space" && !typing && this.active) {
        e.preventDefault();
        this.togglePlay();
      }
    });
  }

  // ---------------------------------------------------------------- layout

  render() {
    const playButton = el("button",
      { type: "button", class: "button primary", "aria-keyshortcuts": "Space" });
    playButton.addEventListener("click", () => this.togglePlay());
    const stepButton = el("button", { type: "button", class: "button", text: "Step +1 s",
      title: "Advance one simulated second" });
    stepButton.addEventListener("click", () => this.advanceBy(1));
    const restartButton = el("button", { type: "button", class: "button", text: "Restart" });
    restartButton.addEventListener("click", () => this.restart());

    const speedGroup = el("div", { class: "segmented", role: "group", "aria-label": "Speed" });
    for (const s of SPEEDS) {
      const b = el("button",
        { type: "button", text: `${s}×`, "aria-pressed": String(s === this.speed) });
      b.addEventListener("click", () => {
        this.speed = s;
        for (const x of speedGroup.querySelectorAll("button")) {
          x.setAttribute("aria-pressed", String(x === b));
        }
      });
      speedGroup.append(b);
    }

    const seedInput = el("input",
      { type: "number", id: "seed", min: 0, step: 1, value: this.seed });
    seedInput.addEventListener("change", () => {
      const v = Math.trunc(Number(seedInput.value));
      if (Number.isFinite(v)) {
        this.seed = v;
        this.restart();
      }
    });
    const newCrowd = el("button", { type: "button", class: "button", text: "New crowd",
      title: "Pick a random seed: new arrival times, walkers and speeds" });
    newCrowd.addEventListener("click", () => {
      this.seed = Math.floor(Math.random() * 100000);
      seedInput.value = this.seed;
      this.restart();
    });

    const strategyBoxes = el("fieldset", { class: "strategies" },
      el("legend", { text: "Strategies" }));
    for (const [name, description] of Object.entries(this.info.strategies)) {
      const box = el("input",
        { type: "checkbox", value: name, checked: this.strategies.includes(name) });
      box.addEventListener("change", () => {
        const chosen = [...strategyBoxes.querySelectorAll("input:checked")].map((b) => b.value);
        if (!chosen.length) {
          box.checked = true; // keep at least one
          return;
        }
        this.strategies = chosen;
        this.onStrategiesChange();
      });
      strategyBoxes.append(el("label", { title: description }, box, ` ${name}`));
    }

    this.clock = el("div", { class: "clock", "aria-live": "off" });
    this.progress = el("progress", { max: 1, value: 0, "aria-label": "Run progress" });
    this.playButton = playButton;
    this.seedInput = seedInput;
    this.strategyBoxes = strategyBoxes;
    this.status = el("p", { class: "run-status", role: "status" });

    const controls = el("div", { class: "controls card" },
      el("div", { class: "control-row" }, playButton, stepButton, restartButton, speedGroup),
      el("div", { class: "control-row" }, this.clock, this.progress),
      el("div", { class: "control-row" }, strategyBoxes,
        el("label", { class: "seed", for: "seed" }, "Seed ", seedInput), newCrowd),
      this.status);

    this.simsGrid = el("div", { class: "sims" });
    this.legend = el("ul", { class: "kind-legend", "aria-label": "Who is who" });
    this.chartLegend = el("ul", { class: "chart-legend" });
    this.chartCanvas = el("canvas", { class: "chart", role: "img",
      "aria-label": "People who have reached the top over time, per strategy" });
    this.chart = new LiveChart(this.chartCanvas);
    this.results = el("section", { class: "card results", hidden: true });

    this.root.replaceChildren(
      controls,
      el("div", { class: "card" }, this.legend, this.simsGrid),
      el("section", { class: "card" },
        el("h2", { class: "card-title", text: "People at the top" }),
        el("p", { class: "card-note",
          text: "When the lines separate, one strategy is carrying more people. "
            + "The dashed line is everyone who has arrived." }),
        this.chartLegend, this.chartCanvas),
      this.results);
    this.renderLegend();
    this.updatePlayButton();
  }

  renderLegend() {
    this.legend.replaceChildren(...Object.entries(this.info.kinds).map(([kind, label]) => {
      const c = el("canvas", { width: 16, height: 16, "aria-hidden": "true" });
      const ctx = c.getContext("2d");
      ctx.fillStyle = cssVar(`--kind-${kind}`);
      ctx.strokeStyle = cssVar("--surface");
      drawShape(ctx, KIND_SHAPES[kind], 8, 8.5, 5);
      return el("li", {}, c, label);
    }));
  }

  buildSimCards() {
    this.cards?.forEach((c) => c.drawing.observer.disconnect());
    this.cards = this.strategies.map((name, i) => {
      const canvas = el("canvas", { class: "escalator", role: "img",
        "aria-label": `${name} escalator, seen from above` });
      const stats = el("dl", { class: "stats" });
      const card = el("article", { class: "sim" },
        el("h3", {},
          el("span", { class: "swatch", style: `background: var(${SERIES_VARS[i]})` }), name),
        el("p", { class: "sim-desc", text: this.info.strategies[name] }),
        canvas, stats);
      return { name, card, stats, drawing: new EscalatorCanvas(canvas) };
    });
    this.simsGrid.style.setProperty("--columns", String(this.cards.length));
    this.simsGrid.replaceChildren(...this.cards.map((c) => c.card));
  }

  /** Pause the animation while another view is showing (the run is kept). */
  setActive(active) {
    this.active = active;
    this.lastFrame = null;
  }

  /**
   * Choose the seed and strategies for the next start() (e.g. "Watch this
   * scenario" from the experiments view). Doesn't restart by itself.
   */
  setScenario({ seed, strategies }) {
    if (Number.isFinite(seed)) {
      this.seed = Math.trunc(seed);
      this.seedInput.value = this.seed;
    }
    const known = (strategies ?? []).filter((s) => s in this.info.strategies);
    if (known.length) {
      this.strategies = known;
      for (const b of this.strategyBoxes.querySelectorAll("input")) {
        b.checked = known.includes(b.value);
      }
    }
  }

  // -------------------------------------------------------------- running

  /** Start (or restart) a run with new settings. */
  async start(values) {
    this.values = values;
    return this.restart();
  }

  async restart() {
    if (!this.values) return;
    const generation = ++this.generation;
    this.busy = true;
    this.owed = 0;
    this.history = { arrived: [], sims: this.strategies.map(() => []) };
    this.results.hidden = true;
    this.status.textContent = "";
    try {
      const state = await this.client.request("live.start", {
        values: this.values, strategies: this.strategies, seed: this.seed, maxQueue: MAX_QUEUE });
      if (generation !== this.generation) return;
      this.buildSimCards();
      this.setState(state);
    } catch (err) {
      if (generation === this.generation) {
        this.status.textContent = `Could not start: ${err.message}`;
      }
    } finally {
      if (generation === this.generation) this.busy = false;
    }
  }

  /** Stop the current run (e.g. the settings became invalid). */
  stop() {
    this.generation++; // ignore replies to requests already sent
    this.busy = false;
    this.state = null; // keeps the last frame on screen but stops advancing
  }

  togglePlay() {
    if (this.state?.done) {
      this.playing = true;
      this.restart();
    } else {
      this.playing = !this.playing;
    }
    this.updatePlayButton();
  }

  updatePlayButton() {
    const done = this.state?.done;
    this.playButton.textContent = done ? "Replay" : this.playing ? "Pause" : "Play";
  }

  tick(now) {
    requestAnimationFrame((t) => this.tick(t));
    const elapsed = this.lastFrame == null
      ? 0 : Math.min((now - this.lastFrame) / 1000, MAX_FRAME_SECONDS);
    this.lastFrame = now;
    if (!this.active || !this.playing || !this.state || this.state.done) return;
    // Owed simulated time; capped so a slow device doesn't build a backlog.
    this.owed = Math.min(this.owed + elapsed * this.speed, this.speed * 0.5 + this.values.dt);
    if (!this.busy && this.owed >= this.values.dt) this.advanceBy(this.owed);
  }

  async advanceBy(seconds) {
    if (this.busy || !this.state || this.state.done) return;
    const generation = this.generation;
    const before = this.state.time;
    this.busy = true;
    try {
      const state = await this.client.request("live.advance", { seconds, maxQueue: MAX_QUEUE });
      if (generation !== this.generation) return;
      this.owed = Math.max(0, this.owed - (state.time - before));
      this.setState(state);
    } catch (err) {
      if (generation === this.generation) {
        this.playing = false;
        this.status.textContent = `Simulation error: ${err.message}`;
      }
    } finally {
      if (generation === this.generation) this.busy = false;
    }
  }

  setState(state) {
    state.generation = this.generation;
    const wasDone = Boolean(this.state?.done) && this.state.generation === this.generation;
    this.state = state;
    this.recordHistory(state);
    this.redraw();
    if (state.done && !wasDone) this.finish();
    this.updatePlayButton();
  }

  recordHistory(state) {
    const h = this.history;
    const last = h.arrived[h.arrived.length - 1];
    if (last && state.time - last[0] < HISTORY_EVERY && !state.done) return;
    h.arrived.push([state.time, state.sims[0].stats.arrived]);
    state.sims.forEach((s, i) => h.sims[i].push([state.time, s.stats.finished]));
  }

  // ------------------------------------------------------------- drawing

  redraw() {
    const state = this.state;
    if (!state || !this.cards) return;
    const duration = this.values.duration;
    this.clock.textContent = `${formatClock(state.time)} / ${formatClock(duration)}`
      + (state.time < this.values.warmup ? " · warm-up" : "");
    this.progress.value = state.time / duration;

    state.sims.forEach((sim, i) => {
      const card = this.cards[i];
      card.drawing.update(sim.snapshot);
      const st = sim.stats;
      const rows = [
        ["Reached the top", String(st.finished)],
        ["Throughput, last 60 s", `${formatNumber(st.throughput_recent, 0)} /min`],
        ["Queueing", st.queue_lengths.join(" | ")],
        ["Average wait so far", `${formatNumber(st.wait_mean)} s`],
        ["Walkers' average trip so far", `${formatNumber(st.trip_mean_cares)} s`],
        ["Others' average trip so far", `${formatNumber(st.trip_mean_others)} s`],
        ["Walked", formatPercent(st.walked_share)],
      ];
      card.stats.replaceChildren(
        ...rows.flatMap(([k, v]) => [el("dt", { text: k }), el("dd", { text: v })]));
    });

    const series = [
      {
        label: "Arrived", color: cssVar("--series-arrived"), dashed: true,
        points: this.history.arrived,
      },
      ...this.strategies.map((name, i) => ({
        label: name, color: cssVar(SERIES_VARS[i]), points: this.history.sims[i] })),
    ];
    this.chart.update({ series, xMax: duration, shadeTo: this.values.warmup });
    this.chartLegend.replaceChildren(...series.map((s) =>
      el("li", { class: s.dashed ? "dashed" : "" },
        el("span", { class: "line", style: `border-color: ${s.color}` }), s.label)));
  }

  async finish() {
    const generation = this.generation;
    let results;
    try {
      results = await this.client.request("live.results");
    } catch (err) {
      this.status.textContent = `Could not compute results: ${err.message}`;
      return;
    }
    if (generation !== this.generation) return;
    this.showResults(results);
  }

  showResults(results) {
    const metrics = [
      ["Throughput", "throughput_per_min", 1, " /min"],
      ["Average wait", "wait_mean", 1, " s"],
      ["95% waited less than", "wait_p95", 1, " s"],
      ["Average trip", "trip_mean", 1, " s"],
      ["Walkers' average trip", "trip_mean_cares", 1, " s"],
      ["Others' average trip", "trip_mean_others", 1, " s"],
      ["Longest queue", "queue_max", 0, ""],
      ["Still queueing at the end", "queue_end", 0, ""],
    ];
    const compareTwo = results.length === 2;
    const head = el("tr", {}, el("th", { scope: "col", text: "" }),
      ...results.map((r) => el("th", { scope: "col", text: r.strategy })),
      compareTwo
        ? el("th", { scope: "col", text: `${results[0].strategy} vs ${results[1].strategy}` })
        : null);
    const rows = metrics.map(([label, key, digits, unit]) => el("tr", {},
      el("th", { scope: "row", text: label }),
      ...results.map((r) => el("td", { text: `${formatNumber(r[key], digits)}${unit}` })),
      compareTwo ? el("td", { text: formatChange(results[0][key], results[1][key]) }) : null));
    const measured = formatClock(results[0].measured_seconds);
    const notes = [WALKERS_NOTE];
    if (compareTwo) {
      const saved = liveTimeSaved(results);
      notes.push(saved.drained ? `${timeSavedLine(saved)}, on this crowd.` : DRAIN_HINT);
    }
    this.results.replaceChildren(
      el("h2", { class: "card-title", text: "Results" }),
      el("p", { class: "card-note",
        text: `Measured over the ${measured} after the warm-up, for seed ${results[0].seed}. `
          + "One run is noisy: use Experiments to average over many crowds." }),
      el("div", { class: "table-wrap" },
        el("table", {}, el("thead", {}, head), el("tbody", {}, ...rows))),
      el("div", { class: "verdict" }, ...notes.map((t) => el("p", { text: t }))));
    this.results.hidden = false;
  }
}
