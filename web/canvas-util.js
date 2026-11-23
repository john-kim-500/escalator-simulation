// Canvas helpers shared by the escalator drawing and the live chart.

/** Read a CSS custom property from :root (so canvases follow the theme). */
export function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

/** Size the canvas backing store to its CSS size × devicePixelRatio. */
export function setupCanvas(canvas) {
  const { width, height } = canvas.getBoundingClientRect();
  if (!width || !height) return null;
  const dpr = window.devicePixelRatio || 1;
  const w = Math.round(width * dpr);
  const h = Math.round(height * dpr);
  if (canvas.width !== w || canvas.height !== h) {
    canvas.width = w;
    canvas.height = h;
  }
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, width, height };
}

/** Redraw when the colour scheme changes. */
export function onThemeChange(callback) {
  window.matchMedia?.("(prefers-color-scheme: dark)").addEventListener?.("change", callback);
}
