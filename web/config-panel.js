// Settings panel built from the engine's PARAM_INFO: one slider + number box
// per parameter, grouped, with help text, field errors, warnings and derived values.

import { formatNumber, roundToStep } from "./format.js";

const OPEN_GROUPS = new Set(["escalator", "crowd"]);

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (value !== false && value != null) node.setAttribute(key, value === true ? "" : value);
  }
  node.append(...children.filter(Boolean));
  return node;
}

export class ConfigPanel {
  /**
   * @param {HTMLElement} root
   * @param {object} info  the worker's `info` reply
   * @param {(values: object) => void} onChange  called (debounced) after edits
   */
  constructor(root, info, onChange) {
    this.root = root;
    this.info = info;
    this.onChange = onChange;
    this.values = { ...info.defaults };
    this.fields = {};
    this.timer = null;
    this.render();
  }

  render() {
    const { param_info: params, groups, strategies } = this.info;
    const form = el("form", { class: "config", novalidate: true });
    form.addEventListener("submit", (e) => e.preventDefault());

    for (const [groupKey, title] of Object.entries(groups)) {
      const body = el("div", { class: "group-body" });
      const group = el("details", { class: "group", open: OPEN_GROUPS.has(groupKey) },
        el("summary", { text: title }), body);
      for (const [name, p] of Object.entries(params)) {
        if (p.group === groupKey) body.append(this.renderField(name, p, strategies));
      }
      form.append(group);
    }

    this.derivedBox = el("dl", { class: "derived", "aria-label": "Calculated values" });
    this.messages = el("div", { class: "messages", "aria-live": "polite" });
    const reset = el("button", { type: "button", class: "button secondary", text: "Reset to defaults" });
    reset.addEventListener("click", () => this.setValues(this.info.defaults));
    this.root.replaceChildren(
      el("h2", { class: "panel-title", text: "Settings" }),
      this.messages, this.derivedBox, form, reset,
    );
  }

  renderField(name, p, strategies) {
    const id = `param-${name}`;
    const value = this.values[name];
    const range = el("input", {
      type: "range", min: p.min, max: p.max, step: p.step, value,
      "aria-label": `${p.label} slider`, tabindex: "-1",
    });
    const number = el("input", {
      type: "number", id, step: p.step, value, inputmode: "decimal",
      "aria-describedby": `${id}-help ${id}-error`,
    });
    const error = el("p", { class: "field-error", id: `${id}-error`, hidden: true });
    const badge = p.only_for
      ? el("span", { class: "badge", text: `${p.only_for.join(", ")} only`,
          title: p.only_for.map((s) => strategies[s]).join(" ") })
      : null;
    const label = el("label", { for: id },
      el("span", { class: "label-text", text: p.label }),
      p.unit ? el("span", { class: "unit", text: p.unit }) : null, badge);

    range.addEventListener("input", () => {
      number.value = roundToStep(Number(range.value), p.step);
      this.edit(name, number.value);
    });
    number.addEventListener("input", () => {
      if (number.value !== "") range.value = number.value;
      this.edit(name, number.value);
    });
    this.fields[name] = { range, number, error, wrapper: null };
    const wrapper = el("div", { class: "field", "data-field": name },
      label,
      el("div", { class: "inputs" }, range, number),
      el("p", { class: "help", id: `${id}-help`, text: p.help }),
      error);
    this.fields[name].wrapper = wrapper;
    return wrapper;
  }

  edit(name, raw) {
    // Keep the raw text so the engine can report "must be a number".
    this.values[name] = raw === "" ? raw : Number(raw);
    clearTimeout(this.timer);
    this.timer = setTimeout(() => this.onChange(this.getValues()), 300);
  }

  getValues() {
    return { ...this.values };
  }

  setValues(values) {
    this.values = { ...this.info.defaults, ...values };
    for (const [name, f] of Object.entries(this.fields)) {
      f.number.value = this.values[name];
      f.range.value = this.values[name];
    }
    clearTimeout(this.timer);
    this.onChange(this.getValues());
  }

  /** Show the engine's check() result: field errors, warnings, derived values. */
  showCheck(result) {
    for (const f of Object.values(this.fields)) {
      f.error.hidden = true;
      f.wrapper.classList.remove("invalid", "warned");
      f.number.removeAttribute("aria-invalid");
    }
    const notes = [];
    for (const { field, message } of result.errors) {
      const f = this.fields[field];
      if (f) {
        f.error.textContent = message;
        f.error.hidden = false;
        f.wrapper.classList.add("invalid");
        f.number.setAttribute("aria-invalid", "true");
        f.wrapper.closest("details").open = true;
      } else {
        notes.push(el("p", { class: "message error", text: message }));
      }
    }
    if (result.errors.length) {
      notes.unshift(el("p", { class: "message error",
        text: "Fix the highlighted settings to restart the simulation." }));
    }
    for (const { field, message } of result.warnings) {
      this.fields[field]?.wrapper.classList.add("warned");
      notes.push(el("p", { class: "message warning", text: `${message}.` }));
    }
    this.messages.replaceChildren(...notes);

    if (result.derived) {
      const d = result.derived;
      const lanes = this.values.lanes;
      const items = [
        ["Escalator length", `${formatNumber(d.length)} m`],
        ["Standing ride", `${formatNumber(d.ride_time, 0)} s`],
        ["Standing lane capacity", `${formatNumber(d.stand_lane_capacity, 0)} /min`],
        ["All lanes standing", `${formatNumber(d.stand_lane_capacity * lanes, 0)} /min`],
        ["Walking lane, at most", `${formatNumber(d.walk_lane_capacity, 0)} /min`],
      ];
      this.derivedBox.replaceChildren(...items.flatMap(([k, v]) => [el("dt", { text: k }), el("dd", { text: v })]));
    }
  }
}
