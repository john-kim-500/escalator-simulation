// Runs the real Python engine inside Pyodide under Node, through the same
// loader the browser worker uses, and checks the results match native Python.
// Needs `npm install` (dev dependency: pyodide). Skipped if it is missing.
import { test, before } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

import { loadEngine, PYODIDE_VERSION, pythonErrorMessage, runExperiment } from "../engine-core.js";

const webDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repoDir = path.resolve(webDir, "..");

let pyodideModule = null;
try {
  pyodideModule = await import("pyodide");
} catch {
  // not installed
}
const skip = pyodideModule ? false : "pyodide is not installed (run npm install)";

let engine;
before(async () => {
  if (skip) return;
  engine = await loadEngine({
    loadPyodide: pyodideModule.loadPyodide,
    readFile: (p) => readFile(path.join(webDir, p), "utf8"),
  });
});

const SHORT = { duration: 180, warmup: 60 };

// Pyodide runs Python 3.14, which sums floats more precisely than Python 3.11,
// so averages can differ in the last few digits. Counts must match exactly.
function assertSameResults(actual, expected) {
  assert.deepEqual(Object.keys(actual).sort(), Object.keys(expected).sort());
  for (const [key, want] of Object.entries(expected)) {
    const got = actual[key];
    if (typeof want === "number" && !Number.isInteger(want)) {
      const close = Math.abs(got - want) <= 1e-9 * Math.max(1, Math.abs(want));
      assert.ok(close, `${key}: ${got} vs ${want}`);
    } else {
      assert.deepEqual(got, want, key);
    }
  }
}

function nativeRun(strategy, seed, overrides) {
  const code = `
import json, sys
from escalator_sim import Simulation, SimConfig
r = Simulation(SimConfig(**json.loads(sys.argv[1])), sys.argv[2], int(sys.argv[3])).run()
print(json.dumps(r))`;
  const args = ["-c", code, JSON.stringify(overrides), strategy, String(seed)];
  const out = execFileSync("python3", args, { cwd: repoDir, encoding: "utf8" });
  return JSON.parse(out);
}

test("installed pyodide matches the pinned CDN version", { skip }, async () => {
  const pkgFile = path.join(repoDir, "node_modules/pyodide/package.json");
  const pkg = JSON.parse(await readFile(pkgFile, "utf8"));
  assert.equal(pkg.version, PYODIDE_VERSION);
});

test("info describes every parameter and strategy", { skip }, () => {
  const info = engine.info();
  assert.ok(info.param_info.arrival_rate);
  assert.deepEqual(Object.keys(info.strategies).sort(), ["stand-both", "walk-left"]);
});

test("a live run in Pyodide gives exactly the native Python results", { skip }, () => {
  engine.liveStart(SHORT, ["stand-both", "walk-left"], 3);
  let state;
  do state = engine.liveAdvance(13.7); while (!state.done);
  const [a, b] = engine.liveResults();
  assertSameResults(a, nativeRun("stand-both", 3, SHORT));
  assertSameResults(b, nativeRun("walk-left", 3, SHORT));
});

test("with the drain on, Pyodide live results equal the native run", { skip }, () => {
  const config = { ...SHORT, arrival_rate: 200, drain: 1 };
  engine.liveStart(config, ["stand-both", "walk-left"], 2);
  let state;
  do state = engine.liveAdvance(50); while (!state.done);
  const [a, b] = engine.liveResults();
  assert.equal(a.drained, 1);
  assertSameResults(a, nativeRun("stand-both", 2, config));
  assertSameResults(b, nativeRun("walk-left", 2, config));
});

test("snapshots carry kinds and a limited queue", { skip }, () => {
  const state = engine.liveStart({ ...SHORT, arrival_rate: 300 }, ["walk-left"], 1, 5);
  const later = engine.liveAdvance(100, 5);
  const lane = later.sims[0].snapshot.lanes[1];
  assert.equal(lane.queue.length, 5);
  assert.ok(lane.queue_length > 5);
  assert.ok(["stander", "walker", "defector", "blocker"].includes(lane.queue[0].kind));
  assert.equal(state.sims.length, 1);
  const { stats } = later.sims[0];
  assert.equal(typeof stats.trip_mean_cares, "number");
  assert.equal(typeof stats.trip_mean_others, "number");
});

test("experiments run step by step", { skip }, () => {
  const { total } = engine.expStart({ kind: "compare", config: { ...SHORT, drain: 0 },
    strategies: ["stand-both", "walk-left"], replications: 2, seed: 1 });
  assert.equal(total, 4);
  let p;
  do p = engine.expStep(0); while (p.done < p.total);
  const { data, winners, time_winners: timeWinners, csv, json } = engine.expResult();
  assert.equal(data.strategies["walk-left"].runs.length, 2);
  assert.equal(winners.length, 1);
  assert.deepEqual(timeWinners, ["-"]); // the drain is off
  assert.equal(data.time_saved[0].drained, false);
  assert.ok(csv.startsWith("strategy,seed,"));
  assert.deepEqual(JSON.parse(json).seeds, [1, 2]);
});

test("runExperiment drives an experiment with progress and cancel", { skip }, async () => {
  const spec = { kind: "sweep", config: SHORT, strategies: ["stand-both", "walk-left"],
    replications: 1, seed: 1, param: "walk_fraction", values: [0, 0.5] };
  const seen = [];
  const out = await runExperiment(engine, spec,
    { onProgress: (p) => seen.push(p.done), sliceSeconds: 0 });
  assert.equal(out.cancelled, false);
  assert.deepEqual(seen, [0, 1, 2, 3, 4]);
  assert.equal(out.result.data.points.length, 2);
  assert.equal(out.result.winners.length, 2);

  let slices = 0;
  const cancelled = await runExperiment(engine, spec,
    { sliceSeconds: 0, isCancelled: () => ++slices > 2 });
  assert.deepEqual(cancelled, { cancelled: true });
  assert.throws(() => engine.expResult(), /experiment not finished/);
});

test("Python errors become readable messages", { skip }, () => {
  const check = engine.check({ walk_fraction: 2 });
  assert.equal(check.ok, false);
  assert.equal(check.errors[0].field, "walk_fraction");
  assert.throws(() => engine.liveStart({ rise: -1 }, ["walk-left"], 1), /rise must be > 0/);
});

test("pythonErrorMessage keeps the last traceback line", () => {
  const err = new Error(
    "Traceback (most recent call last):\n  File ...\nValueError: rise must be > 0\n");
  assert.equal(pythonErrorMessage(err), "rise must be > 0");
});
