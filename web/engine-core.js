// Loads Pyodide and the escalator_sim package and wraps escalator_sim.session.Session.
// Shared by the browser worker (sim-worker.js) and the Node tests, so both run
// exactly the same loading code. Data crosses the JS/Python boundary as JSON strings.

export const PYODIDE_VERSION = "314.0.7";
export const PYODIDE_CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

/**
 * @param {object} opts
 * @param {Function} opts.loadPyodide  loadPyodide from the pyodide package or CDN module
 * @param {(path: string) => Promise<string>} opts.readFile  reads a path relative to web/
 * @param {object} [opts.pyodideOptions]  passed to loadPyodide (e.g. indexURL)
 * @param {(message: string) => void} [opts.onStatus]
 */
export async function loadEngine({
  loadPyodide, readFile, pyodideOptions = {}, onStatus = () => {},
}) {
  onStatus("Loading the Python runtime…");
  const pyodide = await loadPyodide(pyodideOptions);

  onStatus("Loading the simulator…");
  const manifest = JSON.parse(await readFile("manifest.json"));
  pyodide.FS.mkdirTree("/engine/escalator_sim");
  const sources = await Promise.all(
    manifest.files.map((name) => readFile(`${manifest.package_dir}/${name}`)),
  );
  manifest.files.forEach((name, i) => {
    pyodide.FS.writeFile(`/engine/escalator_sim/${name}`, sources[i]);
  });
  pyodide.runPython(`
import sys
sys.path.insert(0, "/engine")
from escalator_sim.session import Session
_session = Session()
`);
  const session = pyodide.globals.get("_session");

  function call(method, ...args) {
    let out;
    try {
      out = session[method](...args);
    } catch (err) {
      throw new Error(pythonErrorMessage(err), { cause: err });
    }
    return out === undefined || out === null ? null : JSON.parse(out);
  }
  const json = (value) => JSON.stringify(value ?? null);

  return {
    pyodideVersion: pyodide.version,
    info: () => call("info"),
    check: (values, strategies = null) => call("check", json(values), json(strategies)),
    liveStart: (values, strategies, seed, maxQueue = 60) =>
      call("live_start", json(values), json(strategies), seed, maxQueue),
    liveAdvance: (seconds, maxQueue = 60) => call("live_advance", seconds, maxQueue),
    liveResults: () => call("live_results"),
    expStart: (spec) => call("exp_start", json(spec)),
    expStep: (budgetSeconds = 0.2) => call("exp_step", budgetSeconds),
    expResult: () => call("exp_result"),
    expCancel: () => call("exp_cancel"),
  };
}

/**
 * Run an experiment to the end in slices, reporting progress. Between slices it
 * awaits `pause()` (the worker uses setTimeout so a cancel message can arrive)
 * and stops early if `isCancelled()` is true.
 * @returns {Promise<{cancelled: true} | {cancelled: false, result: object}>}
 */
export async function runExperiment(engine, spec, {
  onProgress = () => {}, isCancelled = () => false,
  pause = () => new Promise((resolve) => setTimeout(resolve, 0)), sliceSeconds = 0.2,
} = {}) {
  let progress = engine.expStart(spec);
  onProgress(progress);
  while (progress.done < progress.total) {
    await pause();
    if (isCancelled()) {
      engine.expCancel();
      return { cancelled: true };
    }
    progress = engine.expStep(sliceSeconds);
    onProgress(progress);
  }
  return { cancelled: false, result: engine.expResult() };
}

/** The last line of a Python traceback, e.g. "ValueError: rise must be > 0". */
export function pythonErrorMessage(err) {
  const lines = String(err?.message ?? err).trim().split("\n");
  const last = lines[lines.length - 1];
  return last.replace(/^\w+Error: /, "");
}
