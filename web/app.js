// Entry point: starts the engine worker, then builds the settings panel and live view.

import { EngineClient } from "./worker-client.js";
import { ConfigPanel } from "./config-panel.js";
import { LiveView } from "./live-view.js";

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

  // Settings are checked by the engine; a valid change restarts the live run.
  let checkSeq = 0;
  async function applySettings(values) {
    const seq = ++checkSeq;
    const result = await client.request("check", { values, strategies: live.strategies });
    if (seq !== checkSeq) return; // a newer edit superseded this one
    panel.showCheck(result);
    if (result.ok) live.start(result.config);
    else live.stop();
  }
  const panel = new ConfigPanel($("config"), info, applySettings);
  live.onStrategiesChange = () => applySettings(panel.getValues());

  $("loading").hidden = true;
  $("app").hidden = false;
  applySettings(panel.getValues());
}

main();
