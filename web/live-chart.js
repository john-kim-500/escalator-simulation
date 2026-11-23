// Line chart of people over time (canvas), redrawn as the live run advances.

import { cssVar, setupCanvas } from "./canvas-util.js";
import { formatClock, niceStep, niceTimeStep } from "./format.js";

export class LiveChart {
  constructor(canvas) {
    this.canvas = canvas;
    this.data = null;
    new ResizeObserver(() => this.draw()).observe(canvas);
  }

  /**
   * @param {object} data
   * @param {{label: string, color: string, dashed?: boolean, points: number[][]}[]} data.series
   * @param {number} data.xMax  seconds
   * @param {number} [data.shadeTo]  shade [0, shadeTo] (the warm-up)
   */
  update(data) {
    this.data = data;
    this.draw();
  }

  draw() {
    const sized = setupCanvas(this.canvas);
    if (!sized || !this.data) return;
    const { ctx, width, height } = sized;
    const { series, xMax, shadeTo } = this.data;
    const m = { left: 44, right: 12, top: 10, bottom: 24 };
    const w = width - m.left - m.right;
    const h = height - m.top - m.bottom;
    const yDataMax = Math.max(1, ...series.flatMap((s) => s.points.map((p) => p[1])));
    const yStep = niceStep(yDataMax, 4);
    const yMax = Math.ceil(yDataMax / yStep) * yStep;
    const x = (t) => m.left + (t / xMax) * w;
    const y = (v) => m.top + h - (v / yMax) * h;
    const muted = cssVar("--text-muted");

    ctx.clearRect(0, 0, width, height);
    ctx.font = "11px system-ui, sans-serif";

    if (shadeTo > 0) {
      ctx.fillStyle = cssVar("--surface-2");
      ctx.fillRect(m.left, m.top, x(Math.min(shadeTo, xMax)) - m.left, h);
      ctx.fillStyle = muted;
      ctx.textAlign = "left";
      ctx.textBaseline = "top";
      if (x(shadeTo) - m.left > 52) ctx.fillText("warm-up", m.left + 4, m.top + 3);
    }

    // Grid and axes.
    ctx.strokeStyle = cssVar("--grid");
    ctx.lineWidth = 1;
    ctx.fillStyle = muted;
    ctx.beginPath();
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    for (let v = 0; v <= yMax + 1e-9; v += yStep) {
      const yy = Math.round(y(v)) + 0.5;
      ctx.moveTo(m.left, yy);
      ctx.lineTo(m.left + w, yy);
      ctx.fillText(String(Math.round(v)), m.left - 6, yy);
    }
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    const xStep = niceTimeStep(xMax);
    for (let t = 0; t <= xMax + 1e-9; t += xStep) {
      const xx = Math.round(x(t)) + 0.5;
      ctx.moveTo(xx, m.top + h);
      ctx.lineTo(xx, m.top + h + 4);
      ctx.fillText(formatClock(t), xx, m.top + h + 7);
    }
    ctx.stroke();

    // Series.
    ctx.lineWidth = 2;
    ctx.lineJoin = "round";
    for (const s of series) {
      if (!s.points.length) continue;
      ctx.strokeStyle = s.color;
      ctx.setLineDash(s.dashed ? [5, 4] : []);
      ctx.beginPath();
      s.points.forEach(([t, v], i) => (i ? ctx.lineTo(x(t), y(v)) : ctx.moveTo(x(t), y(v))));
      ctx.stroke();
    }
    ctx.setLineDash([]);
  }
}
