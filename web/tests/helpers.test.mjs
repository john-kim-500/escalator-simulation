// Unit tests for pure browser-side helpers (no DOM needed).
import { test } from "node:test";
import assert from "node:assert/strict";

import { formatChange, formatClock, formatNumber, formatPercent, niceStep, niceTimeStep,
  roundToStep } from "../format.js";
import { computeLayout, laneLabel, queueCapacity } from "../escalator-canvas.js";

test("formatting", () => {
  assert.equal(formatNumber(1.234), "1.2");
  assert.equal(formatNumber(null), "–");
  assert.equal(formatNumber(Infinity), "–");
  assert.equal(formatPercent(0.456), "46%");
  assert.equal(formatClock(192.4), "3:12");
  assert.equal(formatClock(59.99999999999), "1:00"); // float noise from steps
  assert.equal(formatClock(600), "10:00");
  assert.equal(formatChange(112, 100), "+12.0%");
  assert.equal(formatChange(90, 100), "−10.0%");
  assert.equal(formatChange(1, 0), "–");
});

test("nice axis steps", () => {
  assert.equal(niceStep(1000, 4), 500);
  assert.equal(niceStep(130, 4), 50);
  assert.equal(niceStep(7, 5), 2);
  assert.equal(niceStep(0), 1);
  assert.equal(niceTimeStep(600), 120);
  assert.equal(niceTimeStep(180), 30);
  assert.equal(niceTimeStep(100000), 3600);
});

test("roundToStep removes float noise from sliders", () => {
  assert.equal(roundToStep(0.30000000000000004, 0.05), 0.3);
  assert.equal(roundToStep(15.5, 0.5), 15.5);
  assert.equal(roundToStep(120, 5), 120);
});

test("layout keeps the escalator and queue inside the canvas", () => {
  const cases = [[300, 420, 2, 30], [160, 380, 2, 120], [600, 560, 4, 4]];
  for (const [width, height, lanes, length] of cases) {
    const L = computeLayout({ width, height, lanes, length });
    assert.ok(L.escTop > 0 && L.escTop < L.escBottom, "escalator has height");
    assert.ok(L.queueTop + L.queueH < height, "queue fits");
    assert.ok(L.x0 >= 0 && L.x0 + L.laneW * lanes <= width, "lanes fit");
    assert.equal(L.posToY(0), L.escBottom);
    assert.equal(L.posToY(length), L.escTop);
    assert.equal(L.posToY(length * 2), L.escTop, "clamped at the top");
    assert.ok(queueCapacity(L) >= 1);
  }
});

test("lane labels", () => {
  assert.equal(laneLabel(0, 2, "walk-left"), "Left · walk");
  assert.equal(laneLabel(1, 2, "walk-left"), "Right · stand");
  assert.equal(laneLabel(1, 2, "stand-both"), "Right");
  assert.equal(laneLabel(2, 3, "stand-both"), "Lane 3");
});

import { ciBounds, defaultRange, downloadName, etaSeconds, formatEta, formatMeanCi, parseList,
  rangeValues, withAlpha } from "../experiment-util.js";

test("sweep ranges have no float noise and respect limits", () => {
  assert.deepEqual(rangeValues(0, 0.5, 0.1).values, [0, 0.1, 0.2, 0.3, 0.4, 0.5]);
  assert.deepEqual(rangeValues(2, 4, 1).values, [2, 3, 4]);
  assert.deepEqual(rangeValues(0, 1, 0.3).values, [0, 0.3, 0.6, 0.9]);
  assert.deepEqual(rangeValues(5, 5, 1).values, [5]);
  assert.match(rangeValues(0, 1, 0).error, /step/);
  assert.match(rangeValues(1, 0, 0.1).error, /less than/);
  assert.match(rangeValues(0, 100, 1).error, /101 values/);
  assert.match(rangeValues(0, NaN, 1).error, /numbers/);
});

test("value lists", () => {
  assert.deepEqual(parseList("0, 0.1,0.25  1").values, [0, 0.1, 0.25, 1]);
  assert.match(parseList("").error, /at least one/);
  assert.match(parseList("1, abc").error, /“abc”/);
});

test("default sweep ranges", () => {
  assert.deepEqual(defaultRange({ min: 0, max: 1, step: 0.05 }), { from: 0, to: 1, step: 0.2 });
  assert.deepEqual(defaultRange({ min: 1, max: 4, step: 1 }), { from: 1, to: 4, step: 1 });
  assert.deepEqual(defaultRange({ min: 0, max: 300, step: 5 }), { from: 0, to: 300, step: 100 });
  const ranges = [
    defaultRange({ min: 0.3, max: 2, step: 0.05 }),
    defaultRange({ min: 60, max: 3600, step: 30 }),
  ];
  for (const r of ranges) {
    assert.ok(rangeValues(r.from, r.to, r.step).values.length >= 2);
  }
});

test("time left and result formatting", () => {
  assert.equal(etaSeconds(10, 0, 100), null);
  assert.equal(etaSeconds(10, 25, 100), 30);
  assert.equal(etaSeconds(10, 100, 100), 0);
  assert.equal(formatEta(null), "estimating time left…");
  assert.equal(formatEta(32), "about 30 s left");
  assert.equal(formatEta(400), "about 7 min left");
  assert.equal(formatMeanCi({ mean: 112.34, ci95: 1.44 }), "112.3 ±1.4");
  assert.equal(formatMeanCi({ mean: 112.34, ci95: null }), "112.3");
  assert.equal(formatMeanCi({ mean: 0.256, ci95: 0.01 }, 0, true), "26%");
  assert.equal(formatMeanCi({ mean: null }), "–");
  assert.deepEqual(ciBounds({ mean: 10, ci95: 2 }), [8, 12]);
  assert.deepEqual(ciBounds({ mean: 10, ci95: null }), [10, 10]);
  assert.equal(downloadName({ seeds: [3], param: "lanes", points: [] }, "csv"),
    "sweep-lanes-seed3.csv");
  assert.equal(downloadName({ seeds: [1], strategies: {} }, "json"), "compare-seed1.json");
});

test("colors with alpha", () => {
  assert.equal(withAlpha("#0b5cad", 0.5), "rgba(11, 92, 173, 0.5)");
  assert.equal(withAlpha(" #fff", 0.2), "rgba(255, 255, 255, 0.2)");
  assert.equal(withAlpha("rgb(1, 2, 3)", 0.1), "rgba(1, 2, 3, 0.1)");
  assert.equal(withAlpha("red", 0.1), "red");
});
