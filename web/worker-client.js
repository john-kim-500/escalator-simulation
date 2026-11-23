// Promise-based wrapper around the simulation worker.

export class EngineClient {
  /**
   * @param {object} [handlers]
   * @param {(message: string) => void} [handlers.onStatus]  loading progress
   * @param {(error: string) => void} [handlers.onFatal]  the engine could not load
   */
  constructor({ onStatus = () => {}, onFatal = () => {} } = {}) {
    this.worker = new Worker(new URL("./sim-worker.js", import.meta.url), { type: "module" });
    this.nextId = 1;
    this.pending = new Map();
    this.worker.onmessage = ({ data }) => {
      if (data.type === "status") return onStatus(data.message);
      if (data.type === "fatal") return this._fail(data.error, onFatal);
      const entry = this.pending.get(data.id);
      if (!entry) return;
      if (data.type === "progress") return entry.onProgress?.(data);
      this.pending.delete(data.id);
      data.ok ? entry.resolve(data.result) : entry.reject(new Error(data.error));
    };
    this.worker.onerror = (event) => {
      event.preventDefault();
      this._fail(event.message || "the simulation worker failed to start", onFatal);
    };
  }

  _fail(error, onFatal) {
    onFatal(error);
    for (const entry of this.pending.values()) entry.reject(new Error(error));
    this.pending.clear();
  }

  /** Send a request; resolves with the worker's result. */
  request(type, args = {}, onProgress = null) {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject, onProgress });
      this.worker.postMessage({ id, type, args });
    });
  }
}
