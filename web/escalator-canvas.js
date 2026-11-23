// Draws one strategy's escalator from a snapshot: a top-down view with the
// bottom of the escalator at the bottom, one column per lane, and the queue
// as a grid below it.

import { cssVar, setupCanvas } from "./canvas-util.js";

export const KIND_SHAPES = {
  stander: "circle",
  walker: "triangle",
  defector: "diamond",
  blocker: "square",
};

/** Geometry of the drawing; pure so it can be unit-tested. */
export function computeLayout({ width, height, lanes, length }) {
  const pad = 10;
  const label = 16;
  const queueH = Math.round(Math.max(64, Math.min(130, height * 0.24)));
  const escTop = pad + label;
  const escBottom = height - pad - label - queueH - 10;
  const rail = 6;
  const laneW = Math.max(18, Math.min(64, (width - 2 * pad - 2 * rail) / lanes));
  const x0 = (width - laneW * lanes) / 2;
  const pxPerM = (escBottom - escTop) / length;
  const r = Math.max(2.5, Math.min(7, pxPerM * 0.24, laneW * 0.22));
  const cell = Math.max(2 * r + 3, 8);
  return {
    width, height, pad, rail, laneW, x0, escTop, escBottom, pxPerM, r, cell,
    queueTop: escBottom + 10,
    queueH,
    queueCols: Math.max(1, Math.floor((laneW - 4) / cell)),
    queueRows: Math.max(1, Math.floor((queueH - 4) / cell)),
    laneCenter: (i) => x0 + laneW * (i + 0.5),
    posToY: (pos) => escBottom - (Math.min(pos, length) / length) * (escBottom - escTop),
  };
}

/** Queue places a lane can show; the rest is summarized as "+N". */
export function queueCapacity(layout) {
  return layout.queueCols * layout.queueRows;
}

export function laneLabel(i, lanes, strategy) {
  const side = lanes === 2 ? ["Left", "Right"][i] : `Lane ${i + 1}`;
  if (strategy === "walk-left") return `${side} · ${i === 0 ? "walk" : "stand"}`;
  return side;
}

export function drawShape(ctx, shape, x, y, r) {
  ctx.beginPath();
  if (shape === "circle") {
    ctx.arc(x, y, r, 0, Math.PI * 2);
  } else if (shape === "triangle") {
    const h = r * 1.25;
    ctx.moveTo(x, y - h);
    ctx.lineTo(x + h * 0.95, y + h * 0.7);
    ctx.lineTo(x - h * 0.95, y + h * 0.7);
    ctx.closePath();
  } else if (shape === "diamond") {
    const h = r * 1.25;
    ctx.moveTo(x, y - h);
    ctx.lineTo(x + h, y);
    ctx.lineTo(x, y + h);
    ctx.lineTo(x - h, y);
    ctx.closePath();
  } else {
    const h = r * 0.9;
    ctx.rect(x - h, y - h, 2 * h, 2 * h);
  }
  ctx.fill();
  ctx.stroke();
}

export class EscalatorCanvas {
  constructor(canvas) {
    this.canvas = canvas;
    this.snapshot = null;
    this.observer = new ResizeObserver(() => this.draw());
    this.observer.observe(canvas);
  }

  update(snapshot) {
    this.snapshot = snapshot;
    this.draw();
  }

  draw() {
    const snap = this.snapshot;
    const sized = setupCanvas(this.canvas);
    if (!sized || !snap) return;
    const { ctx, width, height } = sized;
    const lanes = snap.lanes.length;
    const L = computeLayout({ width, height, lanes, length: snap.length });
    const colors = {
      body: cssVar("--esc-bg"),
      rail: cssVar("--esc-rail"),
      step: cssVar("--esc-step"),
      text: cssVar("--text-muted"),
      outline: cssVar("--surface"),
      queueBg: cssVar("--surface-2"),
      kinds: Object.fromEntries(Object.keys(KIND_SHAPES).map((k) => [k, cssVar(`--kind-${k}`)])),
    };
    ctx.clearRect(0, 0, width, height);
    ctx.font = "11px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    // Escalator body and handrails.
    const left = L.x0 - L.rail;
    const right = L.x0 + L.laneW * lanes + L.rail;
    ctx.fillStyle = colors.body;
    ctx.fillRect(left, L.escTop - 4, right - left, L.escBottom - L.escTop + 8);
    ctx.fillStyle = colors.rail;
    ctx.fillRect(left, L.escTop - 4, L.rail, L.escBottom - L.escTop + 8);
    ctx.fillRect(right - L.rail, L.escTop - 4, L.rail, L.escBottom - L.escTop + 8);

    // Steps move up with the belt; skip some when they would be too dense.
    const stepPx = snap.step_depth * L.pxPerM;
    const every = Math.max(1, Math.ceil(5 / stepPx));
    const spacing = snap.step_depth * every;
    ctx.strokeStyle = colors.step;
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let d = (snap.time * snap.belt_speed) % spacing; d < snap.length; d += spacing) {
      const y = Math.round(L.posToY(d)) + 0.5;
      ctx.moveTo(L.x0, y);
      ctx.lineTo(L.x0 + L.laneW * lanes, y);
    }
    // Lane dividers.
    for (let i = 1; i < lanes; i++) {
      const x = Math.round(L.x0 + L.laneW * i) + 0.5;
      ctx.moveTo(x, L.escTop);
      ctx.lineTo(x, L.escBottom);
    }
    ctx.stroke();

    ctx.fillStyle = colors.text;
    ctx.fillText("▲ top", width / 2, L.pad + 6);

    // People: shape and color by kind, outlined so neighbors stay distinct.
    ctx.strokeStyle = colors.outline;
    ctx.lineWidth = 1;
    const drawPerson = (p, x, y) => {
      ctx.fillStyle = colors.kinds[p.kind] || colors.kinds.stander;
      drawShape(ctx, KIND_SHAPES[p.kind] || "circle", x, y, L.r);
    };
    snap.lanes.forEach((lane, i) => {
      const x = L.laneCenter(i);
      for (const p of lane.people) drawPerson(p, x, L.posToY(p.pos));
    });

    // Queues: a grid per lane, front of the queue nearest the escalator.
    const cap = queueCapacity(L);
    snap.lanes.forEach((lane, i) => {
      const laneLeft = L.x0 + L.laneW * i;
      ctx.fillStyle = colors.queueBg;
      ctx.fillRect(laneLeft + 1, L.queueTop, L.laneW - 2, L.queueH);
      const gridW = L.queueCols * L.cell;
      const gx = laneLeft + (L.laneW - gridW) / 2 + L.cell / 2;
      ctx.strokeStyle = colors.outline;
      const shown = lane.queue.slice(0, cap);
      shown.forEach((p, k) => {
        const row = Math.floor(k / L.queueCols);
        const col = k % L.queueCols;
        drawPerson(p, gx + col * L.cell, L.queueTop + 2 + L.cell / 2 + row * L.cell);
      });
      const hidden = lane.queue_length - shown.length;
      ctx.fillStyle = colors.text;
      ctx.fillText(
        hidden > 0 ? `${lane.queue_length} (+${hidden})` : String(lane.queue_length),
        L.laneCenter(i), L.queueTop + L.queueH + 9,
      );
      ctx.fillText(laneLabel(i, lanes, snap.strategy), L.laneCenter(i), height - L.pad + 2);
    });
  }
}
