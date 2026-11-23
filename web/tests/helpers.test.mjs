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
  for (const [width, height, lanes, length] of [[300, 420, 2, 30], [160, 380, 2, 120], [600, 560, 4, 4]]) {
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
