"use strict";

const byId = (id) => document.getElementById(id);
const number = (n) => typeof n === "number" && Number.isFinite(n);
const mode = byId("mode");
const step = byId("step");
const units = byId("units");
const ns = "http://www.w3.org/2000/svg";
const embedded = byId("replay-data");
const replayData = embedded ? JSON.parse(embedded.textContent) : null;
if (replayData) {
  const liveOption = mode.querySelector('option[value="live"]');
  liveOption.textContent = "Live · Server required";
  liveOption.disabled = true;
  liveOption.hidden = true;
}
const supportedModes = Array.from(mode.options, (option) => option.value);
const params = new URLSearchParams(location.search);
if (supportedModes.includes(params.get("mode"))) mode.value = params.get("mode");

let report = null;
let selected = null;
let requestId = 0;
let scrubTimer;
let currentController;
let copyReset;

function text(id, value) {
  byId(id).textContent = value == null ? "—" : String(value);
}

function asDate(value) {
  const ms = value ? Date.parse(value) : NaN;
  return Number.isFinite(ms) ? new Date(ms) : null;
}

function dateText(value) {
  return asDate(value)?.toISOString().slice(0, 19).replace("T", " ") ?? "Unavailable";
}

function ageText(seconds) {
  if (seconds < 60) return seconds + " s";
  if (seconds < 3600) return Math.floor(seconds / 60) + " min " + (seconds % 60) + " s";
  if (seconds < 86400) return Math.floor(seconds / 3600) + " h " + Math.floor(seconds % 3600 / 60) + " min";
  return Math.floor(seconds / 86400) + " d " + Math.floor(seconds % 86400 / 3600) + " h";
}

function signed(value, decimals = 1) {
  if (!number(value)) return "—";
  const rounded = Math.abs(value).toFixed(decimals);
  return (Number(rounded) === 0 ? "" : value < 0 ? "−" : "+") + rounded;
}

function stateClass(state) {
  const value = String(state).toLowerCase();
  return ["normal", "watch", "incident", "unknown"].includes(value) ? value : "unknown";
}

function activeAsset() {
  return report?.assets.find((asset) => asset.id === selected);
}

function sourceBadge(live) {
  const badge = byId("source-badge");
  badge.textContent = live ? "Live collection" : "Synthetic replay";
  badge.classList.toggle("live", live);
}

function renderAssetList() {
  const target = byId("asset-list");
  const focusId = document.activeElement?.dataset.assetId;
  target.replaceChildren();
  for (const asset of report.assets) {
    const button = document.createElement("button");
    button.className = "asset";
    button.type = "button";
    button.dataset.assetId = String(asset.id);
    button.setAttribute("aria-pressed", String(asset.id === selected));
    const left = document.createElement("span");
    const name = document.createElement("span");
    name.className = "asset-symbol";
    name.textContent = asset.symbol;
    const deviation = document.createElement("span");
    deviation.className = "asset-bps";
    deviation.textContent = number(asset.bps) ? signed(asset.bps) + " bp" : "No quote";
    const status = document.createElement("span");
    status.className = "asset-state " + stateClass(asset.state);
    status.textContent = asset.state;
    left.append(name, deviation);
    button.append(left, status);
    button.addEventListener("click", () => {
      selected = asset.id;
      resetCopy();
      renderAssetList();
      renderSelected();
      text("announcements", asset.symbol + " selected. " + asset.state + ". " + asset.reason);
    });
    target.append(button);
    if (focusId === String(asset.id)) button.focus({preventScroll:true});
  }
}

function svgEl(parent, name, attributes, content = "") {
  const elem = document.createElementNS(ns, name);
  for (const [key,value] of Object.entries(attributes)) elem.setAttribute(key, String(value));
  if (content) elem.textContent = content;
  parent.append(elem);
  return elem;
}

function chart(asset) {
  const target = byId("chart");
  target.replaceChildren();
  const points = (asset.series || []).map((p) => ({value:p.bps, ms:asDate(p.at)?.getTime()}))
    .filter((p) => number(p.ms)).sort((a,b) => a.ms - b.ms);
  const valid = points.filter((p) => number(p.value));
  text("chart-caption", "Observed deviation in basis points. The solid horizontal line marks the $1 peg. Times are UTC.");
  if (!valid.length) {
    const note = document.createElement("p");
    note.className = "chart-empty";
    note.textContent = "Awaiting a valid price observation.";
    target.append(note);
    return;
  }
  const W = 558, H = 148, L = 49, R = 14, T = 12, B = 28;
  const svg = svgEl(target, "svg", {viewBox:"0 0 " + W + " " + H, role:"img", "aria-labelledby":"chart-title chart-description"});
  svgEl(svg, "title", {id:"chart-title"}, asset.symbol + " deviation history");
  const extrema = valid.map((p) => p.value);
  svgEl(svg, "desc", {id:"chart-description"}, valid.length + " observations from " + dateText(new Date(valid[0].ms).toISOString()) + " UTC to " + dateText(new Date(valid.at(-1).ms).toISOString()) + " UTC. Observed range " + signed(Math.min(...extrema)) + " to " + signed(Math.max(...extrema)) + " basis points.");
  const desired = Math.max(10, ...extrema.map(Math.abs));
  const magnitude = 10 ** Math.floor(Math.log10(desired));
  const limit = Math.ceil(desired / magnitude / 0.5) * 0.5 * magnitude;
  const start = points[0].ms, end = points.at(-1).ms;
  const px = (m) => start === end ? (W + L - R)/2 : L + (m - start) / (end - start) * (W - L - R);
  const py = (v) => T + (limit - v) / (limit * 2) * (H - B - T);
  for (const tick of [limit,0,-limit]) {
    svgEl(svg, "line", {x1:L, x2:W-R, y1:py(tick), y2:py(tick), class:tick === 0 ? "peg" : "grid"});
    svgEl(svg, "text", {x:L-7, y:py(tick)+4, "text-anchor":"end"}, signed(tick, Number.isInteger(tick) ? 0 : 1));
  }
  let path = "", last = null;
  for (const p of points) {
    if (!number(p.value)) { last = null; continue; }
    const command = last === null || p.ms - last > 180000 ? "M" : "L";
    path += command + px(p.ms) + "," + py(p.value) + " ";
    last = p.ms;
  }
  svgEl(svg,"path",{d:path, class:"trace"});
  for (const [index,p] of valid.entries()) {
    const circle = svgEl(svg,"circle",{cx:px(p.ms), cy:py(p.value), r:index === valid.length-1 ? 4.3 : 2.5, class:"point"});
    svgEl(circle,"title",{}, new Date(p.ms).toISOString() + " · " + signed(p.value) + " bp");
  }
  const time = (ms) => new Date(ms).toISOString().slice(11,19);
  svgEl(svg,"text",{x:L, y:H-7},time(start));
  if (end !== start) svgEl(svg,"text",{x:W-R, y:H-7, "text-anchor":"end"},time(end));
}

function refreshAge() {
  const asset = activeAsset();
  if (!asset) return;
  const live = report.mode === "live";
  const updated = asDate(asset.updated);
  const asOf = asDate(report.as_of);
  const now = live ? Date.now() : asOf?.getTime();
  const age = updated && number(now) ? Math.floor((now - updated.getTime())/1000) : null;
  text("age-label", live ? "Quote age now" : "Age at replay frame");
  text("quote-age", age == null ? "Unavailable" : age < 0 ? "Future timestamp" : ageText(age));
  const warning = byId("age-warning");
  warning.hidden = !live || age == null || (age >= 0 && age <= 180);
  if (!warning.hidden) warning.textContent = age < 0
    ? "The quote is ahead of the current clock. Verify its timestamp before using this report."
    : "This quote is now outside the 180-second freshness window. The displayed state was evaluated at report time.";
}

function tooOldOnScreen(asset) {
  if (report?.mode !== "live") return false;
  const updated = asDate(asset.updated);
  if (!updated) return true;
  const age = (Date.now() - updated.getTime()) / 1000;
  return age < 0 || age > 180;
}

function briefFor(asset, mark) {
  const state = tooOldOnScreen(asset) ? "Unknown" : asset.state;
  const hasQuote = number(asset.bps) && stateClass(state) !== "unknown";
  const first = asset.symbol + " / USD · " + state + (hasQuote ? " · " + signed(asset.bps) + " bp" : "") + ".";
  const reason = tooOldOnScreen(asset) && asset.state !== "Unknown" ? "The last quote is outside the live freshness window." : asset.reason;
  const next = {
    normal:"Continue sampling for a fresh deviation.",
    watch:"Check the next distinct source quote for confirmation.",
    incident:"Verify independent venue prices and the issuer’s redemption status.",
    unknown:"Check collection health and the upstream timestamp before escalating a peg alert."
  }[stateClass(state)];
  const quantity = Intl.NumberFormat("en-US", {maximumFractionDigits:6}).format(units.valueAsNumber);
  const impactLine = mark ? "Illustrative mark for " + quantity + " units: " + mark + " vs $1." : "Illustrative mark unavailable.";
  const update = asDate(asset.updated) ? dateText(asset.updated) + " UTC" : "unavailable";
  return [first + " " + reason, impactLine, "Next: " + next,
    "Quote updated: " + update + " · " + report.source].join("\n\n");
}

function renderEvents(asset) {
  const events = Array.isArray(asset.events) ? asset.events.slice(-3).reverse() : [];
  const list = byId("changes");
  list.replaceChildren();
  byId("changes-panel").hidden = !events.length;
  for (const event of events) {
    const item = document.createElement("li");
    const state = document.createElement("b");
    state.className = "asset-state " + stateClass(event.state);
    state.textContent = event.state;
    const at = document.createElement("time");
    at.dateTime = event.at;
    at.textContent = dateText(event.at);
    item.append(state,at);
    list.append(item);
  }
}

function impact() {
  const asset = activeAsset();
  const amount = units.valueAsNumber;
  const eligible = asset && number(asset.price) && stateClass(asset.state) !== "unknown" && !tooOldOnScreen(asset) && units.validity.valid && number(amount);
  const signedUsd = eligible ? new Intl.NumberFormat("en-US", {style:"currency", currency:"USD", signDisplay:"exceptZero"}).format(amount * (asset.price - 1)) : null;
  text("impact-value", signedUsd ?? "Unavailable");
  text("impact-detail", !units.validity.valid || !number(amount) ? "Enter a quantity between 0 and 1 trillion units." : asset && (stateClass(asset.state) === "unknown" || tooOldOnScreen(asset)) ? "A fresh, valid quote is required for a marked value." : "Illustrative change at the reported quote, before fees or slippage.");
  if (asset) text("brief", briefFor(asset, signedUsd));
}

function renderSelected() {
  const asset = activeAsset();
  if (!asset) return;
  text("focus-title", asset.symbol + " / USD");
  text("focus-state", asset.state);
  byId("focus-state").className = "status " + stateClass(asset.state);
  text("focus-bps", number(asset.bps) ? signed(asset.bps) + " bp" : "—");
  text("focus-price", number(asset.price) ? "$" + asset.price.toFixed(6) : "Unavailable");
  text("reason", asset.reason);
  text("quote-time", dateText(asset.updated));
  chart(asset);
  renderEvents(asset);
  refreshAge();
  impact();
}

function optionalEvidence(slot, id, value) {
  byId(slot).hidden = value == null || value === "";
  text(id,value);
}

function renderEvidence() {
  const evidence = report.evidence;
  text("report-source", report.source);
  optionalEvidence("evidence-slot", "call-source", evidence?.source);
  optionalEvidence("endpoint-slot", "endpoint", evidence?.endpoint);
  optionalEvidence("fetched-slot", "fetched", evidence?.fetched_at ? dateText(evidence.fetched_at) : null);
  optionalEvidence("credit-slot", "credits", evidence?.credit_count);
  const note = replayData ? "This offline demo uses generated prices. Live API receipts are available in the server edition." : report.mode !== "live" ? "This replay uses generated prices. Open Live for the latest collected API receipt." : evidence ? "The dashboard checks the local capture store every 15 seconds." : "No call receipt is available for this report.";
  text("evidence-note", note);
}

function resetCopy() {
  clearTimeout(copyReset);
  text("copy","Copy brief");
  byId("copy-manual").hidden = true;
}

function updateUrl() {
  if (location.protocol === "file:") return;
  const url = new URL(location.href);
  url.searchParams.set("mode", report.mode);
  if (report.mode !== "live") url.searchParams.set("step", String(report.step));
  else url.searchParams.delete("step");
  try { history.replaceState(null,"",url); } catch { /* Sandboxed viewers may disable history. */ }
}

function paint(payload) {
  report = payload;
  const assets = report.assets;
  if (!assets.some((asset) => asset.id === selected)) selected = (assets.find((asset) => asset.symbol === "USDC") || assets[0]).id;
  byId("empty").hidden = true;
  byId("results").hidden = false;
  sourceBadge(report.mode === "live");
  text("observed", dateText(report.as_of));
  byId("observed").dateTime = report.as_of;
  byId("step-box").hidden = report.mode === "live";
  if (report.mode !== "live") {
    step.max = report.steps;
    step.value = report.step;
    step.setAttribute("aria-valuetext", "Frame " + report.step + " of " + report.steps);
    text("frame", report.step + " / " + report.steps);
  }
  renderAssetList();
  renderSelected();
  renderEvidence();
  updateUrl();
}

async function load(frame, background = false) {
  clearTimeout(scrubTimer);
  const sequence = ++requestId;
  currentController?.abort();
  currentController = new AbortController();
  const route = mode.value;
  const changingSource = report?.mode !== route;
  if (changingSource) {
    report = null;
    byId("results").hidden = true;
    byId("step-box").hidden = true;
    text("observed","—");
    byId("observed").removeAttribute("datetime");
  }
  byId("empty").hidden = true;
  byId("results").setAttribute("aria-busy","true");
  sourceBadge(route === "live");
  byId("refresh").disabled = true;
  if (!background) resetCopy();
  const query = new URLSearchParams({mode:route});
  if (route !== "live" && Number.isInteger(frame) && frame > 0) query.set("step", String(frame));
  try {
    let data;
    if (replayData) {
      if (route === "live") throw new Error("The offline demo contains four synthetic replays. Live observations require the local server.");
      const frames = replayData[route] || [];
      const index = query.has("step") ? Number(query.get("step")) - 1 : frames.length - 1;
      data = frames[index];
      if (!data) throw new Error("This replay frame does not exist.");
    } else {
      const response = await fetch("/api/report?" + query, {cache:"no-store", signal:currentController.signal});
      data = await response.json();
      if (sequence !== requestId) return;
      if (!response.ok) throw new Error(data.error || "The report request failed.");
    }
    if (!Array.isArray(data.assets) || !data.assets.length) throw new Error("No observations are available for this view.");
    paint(data);
    text("announcements", data.source + ". Report time " + dateText(data.as_of) + " UTC.");
  } catch (error) {
    if (sequence !== requestId || error.name === "AbortError") return;
    report = null;
    byId("results").hidden = true;
    byId("step-box").hidden = true;
    text("observed","—");
    byId("observed").removeAttribute("datetime");
    byId("empty").hidden = false;
    text("empty-title", route === "live" ? "Live report unavailable" : "Unable to open this replay");
    text("empty-message", error.message + (route === "live" ? " Run a live collection on the server, then refresh this view. You can explore a synthetic replay in the meantime." : " Select Refresh to try again."));
  } finally {
    if (sequence === requestId) {
      byId("refresh").disabled = false;
      byId("results").removeAttribute("aria-busy");
    }
  }
}

mode.addEventListener("change", () => load());
byId("refresh").addEventListener("click", () => load(report?.step));
step.addEventListener("input", () => {
  text("frame", step.value + " / " + step.max);
  clearTimeout(scrubTimer);
  const requested = Number(step.value);
  scrubTimer = setTimeout(() => load(requested),60);
});
units.addEventListener("input", impact);
byId("copy").addEventListener("click", async () => {
  if (!report) return;
  impact();
  const brief = byId("brief").textContent;
  try {
    await navigator.clipboard.writeText(brief);
    text("copy","Copied");
    text("announcements","Triage brief copied.");
    clearTimeout(copyReset);
    copyReset = setTimeout(resetCopy,2200);
  } catch {
    byId("copy-manual").hidden = false;
    const field = byId("copy-text");
    field.value = brief;
    field.focus();
    field.select();
    text("announcements","The brief is selected for copying.");
  }
});
setInterval(() => {
  if (replayData || document.hidden || mode.value !== "live") return;
  if (report) { refreshAge(); impact(); }
  if (!byId("refresh").disabled) load(undefined, true);
},15000);
load(Number(params.get("step")));
