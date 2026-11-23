// Web Worker: runs the Python engine so the page never freezes.
// Protocol: the page sends {id, type, args}; the worker replies
// {id, ok: true, result} or {id, ok: false, error}. It also sends
// {type: "status", message} while loading and {id, type: "progress", done, total}
// during experiments.

import { loadEngine, PYODIDE_CDN, runExperiment } from "./engine-core.js";

const base = new URL("./", import.meta.url);

const ready = (async () => {
  const { loadPyodide } = await import(`${PYODIDE_CDN}pyodide.mjs`);
  const engine = await loadEngine({
    loadPyodide,
    pyodideOptions: { indexURL: PYODIDE_CDN },
    readFile: async (path) => {
      // Always check with the server: simple servers (python3 -m http.server)
      // send no caching rules, so the browser could otherwise mix old and new
      // copies of the package's files after an update.
      const response = await fetch(new URL(path, base), { cache: "no-cache" });
      if (!response.ok) throw new Error(`could not load ${path} (HTTP ${response.status})`);
      return response.text();
    },
    onStatus: (message) => postMessage({ type: "status", message }),
  });
  postMessage({ type: "status", message: "Ready" });
  return engine;
})();
ready.catch((err) => postMessage({ type: "fatal", error: String(err?.message ?? err) }));

let cancelRequested = false;

const handlers = {
  info: (engine) => ({ ...engine.info(), pyodide: engine.pyodideVersion }),
  check: (engine, { values, strategies }) => engine.check(values, strategies),
  "live.start": (engine, { values, strategies, seed, maxQueue }) =>
    engine.liveStart(values, strategies, seed, maxQueue),
  "live.advance": (engine, { seconds, maxQueue }) => engine.liveAdvance(seconds, maxQueue),
  "live.results": (engine) => engine.liveResults(),
  "exp.run": (engine, { spec }, id) => {
    cancelRequested = false;
    return runExperiment(engine, spec, {
      onProgress: ({ done, total }) => postMessage({ id, type: "progress", done, total }),
      isCancelled: () => cancelRequested, // set by an "exp.cancel" message between slices
    });
  },
  "exp.cancel": () => {
    cancelRequested = true;
    return true;
  },
};

self.onmessage = async ({ data }) => {
  const { id, type, args = {} } = data;
  try {
    const engine = await ready;
    const handler = handlers[type];
    if (!handler) throw new Error(`unknown request ${type}`);
    postMessage({ id, ok: true, result: await handler(engine, args, id) });
  } catch (err) {
    postMessage({ id, ok: false, error: String(err?.message ?? err) });
  }
};
