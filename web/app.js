// Entry point: starts the engine worker, then builds the settings panel and live view.

import { EngineClient } from "./worker-client.js";
import { ConfigPanel } from "./config-panel.js";
import { LiveView } from "./live-view.js";
import { ExperimentsView } from "./experiments-view.js";

const $ = (id) => document.getElementById(id);

function showFatal(title, detail) {
  $("loading").hidden = true;
  const box = $("fatal");
  box.replaceChildren();
  const h = document.createElement("h2");
  h.textContent = title;
  const p = document.createElement("p");
  p.textContent = detail;
  box.append(h, p);
  box.hidden = false;
}

async function main() {
  if (location.protocol === "file:") {
    showFatal("This page needs a web server",
      "Browsers block the simulation worker on file:// pages. From the project folder run "
      + "`python3 -m http.server 8000` and open http://localhost:8000/web/");
    return;
  }

  const client = new EngineClient({
    onStatus: (message) => ($("loading-message").textContent = message),
    onFatal: (error) => showFatal("The simulator could not start",
      `${error}. It downloads the Python runtime from cdn.jsdelivr.net, so it needs internet access.`),
  });

  let info;
  try {
    info = await client.request("info");
  } catch (err) {
    showFatal("The simulator could not start", err.message);
    return;
  }
  $("engine-version").textContent = `Engine ${info.version} · Pyodide ${info.pyodide}`;

  const live = new LiveView($("live"), client, info);
  let lastCheck = null;
  const experiments = new ExperimentsView($("experiments"), client, info, {
    getSettings: () => lastCheck,
    onWatch: ({ config, seed, strategies }) => {
      live.setScenario({ seed, strategies });
      showView("live");
      panel.setValues(config); // checks the settings, then restarts the live run
      window.scrollTo({ top: 0 });
    },
  });

  // Settings are checked by the engine; a valid change restarts the live run.
  let checkSeq = 0;
  async function applySettings(values) {
    const seq = ++checkSeq;
    let result;
    try {
      result = await client.request("check", { values, strategies: live.strategies });
    } catch (err) {
      result = { ok: false, errors: [{ field: "", message: err.message }], warnings: [], derived: null, config: null };
    }
    if (seq !== checkSeq) return; // a newer edit superseded this one
    lastCheck = result;
    panel.showCheck(result);
    experiments.settingsChanged();
    if (result.ok) live.start(result.config);
    else live.stop();
  }
  const panel = new ConfigPanel($("config"), info, applySettings);
  live.onStrategiesChange = () => applySettings(panel.getValues());

  // Live / Experiments tabs. The live animation pauses while hidden.
  const tabs = $("view-tabs");
  function showView(view) {
    for (const b of tabs.querySelectorAll("button")) b.setAttribute("aria-pressed", String(b.dataset.view === view));
    $("live").hidden = view !== "live";
    $("experiments").hidden = view !== "experiments";
    live.setActive(view === "live");
  }
  tabs.addEventListener("click", (e) => {
    const view = e.target.closest("button")?.dataset.view;
    if (view) showView(view);
  });

  $("loading").hidden = true;
  $("app").hidden = false;
  tabs.hidden = false;
  applySettings(panel.getValues());
}

main();
