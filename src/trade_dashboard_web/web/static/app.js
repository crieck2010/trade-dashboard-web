"use strict";
// Minimal vanilla-JS client. No dependencies, no build step.

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

async function api(method, path, body) {
  const res = await fetch(path, {
    method,
    headers: {"Content-Type": "application/json"},
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

// -- tabs -----------------------------------------------------------------
document.querySelectorAll("#tabs button").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("#tabs button").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    btn.classList.add("active");
    $("tab-" + btn.dataset.tab).classList.add("active");
  });
});

// -- svg charts ------------------------------------------------------------
function lineChart(points, {stroke = "#5aa2ff", fill = "rgba(90,162,255,.15)"} = {}) {
  const W = 900, H = 260, P = 8;
  if (!points.length) return "";
  const min = Math.min(...points), max = Math.max(...points);
  const span = max - min || 1;
  const x = (i) => P + (i / Math.max(points.length - 1, 1)) * (W - 2 * P);
  const y = (v) => H - P - ((v - min) / span) * (H - 2 * P);
  const line = points.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">` +
    `<path d="${line} L${x(points.length-1).toFixed(1)},${H} L${x(0).toFixed(1)},${H} Z" fill="${fill}" stroke="none"/>` +
    `<path d="${line}" fill="none" stroke="${stroke}" stroke-width="2" vector-effect="non-scaling-stroke"/></svg>`;
}

function candleChart(bars) {
  const W = 900, H = 260, P = 8;
  const data = bars.slice(-120);
  if (!data.length) return "";
  const min = Math.min(...data.map((b) => b.low)), max = Math.max(...data.map((b) => b.high));
  const span = max - min || 1;
  const n = data.length, bw = (W - 2 * P) / n;
  const y = (v) => H - P - ((v - min) / span) * (H - 2 * P);
  let s = `<svg class="chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">`;
  data.forEach((b, i) => {
    const cx = P + bw * (i + 0.5), up = b.close >= b.open, col = up ? "#3fd08c" : "#ff6b6b";
    s += `<line x1="${cx.toFixed(1)}" y1="${y(b.high).toFixed(1)}" x2="${cx.toFixed(1)}" y2="${y(b.low).toFixed(1)}" stroke="${col}" stroke-width="1"/>` +
      `<rect x="${(cx - bw * 0.3).toFixed(1)}" y="${y(Math.max(b.open, b.close)).toFixed(1)}" width="${(bw * 0.6).toFixed(1)}" height="${Math.max(1, Math.abs(y(b.open) - y(b.close))).toFixed(1)}" fill="${col}"/>`;
  });
  return s + "</svg>";
}

function table(rows, cols) {
  if (!rows.length) return '<span class="hint">none</span>';
  return "<table><tr>" + cols.map((c) => `<th>${esc(c[1])}</th>`).join("") + "</tr>" +
    rows.map((r) => "<tr>" + cols.map((c) => `<td>${esc(fmtCell(r[c[0]]))}</td>`).join("") + "</tr>").join("") + "</table>";
}
function fmtCell(v) {
  if (v === null || v === undefined) return "";
  if (typeof v === "number") return Math.abs(v) < 0.01 && v !== 0 ? v.toExponential(2) : v.toFixed(4).replace(/\.?0+$/, "");
  if (typeof v === "object") return JSON.stringify(v);
  return v;
}

// -- data tab ---------------------------------------------------------------
async function loadSources() {
  const sources = await api("GET", "/api/sources");
  for (const id of ["bt-source", "desk-source", "data-source"]) {
    const sel = $(id);
    sel.innerHTML = sources.map((s) =>
      `<option value="${esc(s.id)}"${s.available ? "" : " disabled"}>${esc(s.label)}${s.available ? "" : " (unavailable)"}</option>`).join("");
  }
}

$("data-fetch").addEventListener("click", async () => {
  $("data-error").textContent = "";
  try {
    const d = await api("GET", `/api/bars?symbol=${encodeURIComponent($("data-symbol").value)}&source=${$("data-source").value}&days=365`);
    $("data-chart").innerHTML = candleChart(d.bars);
    const last = d.bars[d.bars.length - 1];
    $("data-info").textContent = `${d.bars.length} daily bars · last close ${last.close.toFixed(2)} @ ${last.timestamp.slice(0, 10)}`;
  } catch (e) { $("data-error").textContent = e.message; }
});

// -- strategies tab ----------------------------------------------------------
async function loadStrategies() {
  const list = await api("GET", "/api/strategies");
  $("strat-list").innerHTML = list.map((s) =>
    `<div class="strat"><h4>${esc(s.name)}</h4><code>${esc(s.family || "")}</code><p>${esc(s.description || "")}</p>` +
    `<p><b>params:</b> <code>${esc(JSON.stringify(s.parameters || {}))}</code></p></div>`).join("");
  $("bt-strategy").innerHTML = list.map((s) => `<option>${esc(s.name)}</option>`).join("");
}

// -- backtest tab -------------------------------------------------------------
$("bt-run").addEventListener("click", async () => {
  $("bt-error").textContent = "";
  const btn = $("bt-run"); btn.disabled = true; btn.textContent = "Running…";
  try {
    const r = await api("POST", "/api/backtest", {
      strategy: $("bt-strategy").value,
      symbols: $("bt-symbols").value.split(",").map((s) => s.trim()).filter(Boolean),
      params: JSON.parse($("bt-params").value || "{}"),
      source: $("bt-source").value,
      initial_cash: parseFloat($("bt-cash").value) || 100000,
    });
    $("bt-chart").innerHTML = lineChart(r.equity_curve.map((p) => p.equity));
    const m = r.metrics;
    const order = ["total_return", "cagr", "sharpe_ratio", "sortino_ratio", "max_drawdown", "calmar_ratio", "annualized_volatility", "num_trades", "win_rate", "profit_factor"];
    $("bt-metrics").innerHTML = order.filter((k) => k in m).map((k) =>
      `<div class="metric"><b class="${m[k] >= 0 ? "pos" : "neg"}">${fmtCell(m[k])}</b><span>${esc(k)}</span></div>`).join("") +
      `<div class="metric"><b>${fmtCell(r.final_equity)}</b><span>final_equity</span></div>`;
    $("bt-trades").innerHTML = table(r.trades.slice(-50).reverse(),
      [["symbol","sym"],["entry_time","entry"],["exit_time","exit"],["quantity","qty"],["entry_price","in"],["exit_price","out"],["pnl","pnl"],["return_pct","ret%"]]);
  } catch (e) { $("bt-error").textContent = e.message; }
  finally { btn.disabled = false; btn.textContent = "Run backtest"; }
});

// -- desk tab ------------------------------------------------------------------
$("desk-run").addEventListener("click", async () => {
  $("desk-error").textContent = "";
  const btn = $("desk-run"); btn.disabled = true; btn.textContent = "Running desk…";
  try {
    const r = await api("POST", "/api/desk", {
      symbols: $("desk-symbols").value.split(",").map((s) => s.trim()).filter(Boolean),
      equity: parseFloat($("desk-equity").value) || 100000,
      source: $("desk-source").value,
    });
    const nIdeas = r.briefs.reduce((a, b) => a + b.ideas.length, 0);
    $("desk-summary").textContent =
      `${r.briefs.length} briefs · ${nIdeas} ideas · ${r.allocations.length} allocations · ` +
      `${r.approved_orders.length} approved · ${r.vetoes.length} vetoed`;
    $("desk-briefs").innerHTML = r.briefs.map((b) =>
      `<div class="brief"><b>${esc(b.agent)}</b> <span class="hint">${esc(b.niche)} — ${b.ideas.length} ideas</span>` +
      b.ideas.map((i) =>
        `<div class="hint">${esc(i.direction.toUpperCase())} ${esc(i.symbol)} · ${esc(i.strategy)} ` +
        `score=${i.score.toFixed(2)} conv=${i.conviction.toFixed(2)} ` +
        `sharpe=${(i.metrics.sharpe_ratio || 0).toFixed(2)} dd=${((i.metrics.max_drawdown || 0) * 100).toFixed(1)}%</div>`).join("") +
      `</div>`).join("");
    $("desk-allocs").innerHTML = table(r.allocations.map((a) => ({
      symbol: a.idea.symbol, dir: a.idea.direction, weight: (a.weight * 100).toFixed(1) + "%",
      qty: a.quantity == null ? "" : (+a.quantity).toFixed(2), strategy: a.idea.strategy, score: a.idea.score.toFixed(2),
    })), [["symbol","symbol"],["dir","dir"],["weight","weight"],["qty","qty"],["strategy","strategy"],["score","score"]]);
    $("desk-vetoes").innerHTML = table(r.vetoes.map((v) => ({
      symbol: v.order.symbol, limit: v.limit, reason: v.reason,
    })), [["symbol","symbol"],["limit","limit"],["reason","reason"]]);
  } catch (e) { $("desk-error").textContent = e.message; }
  finally { btn.disabled = false; btn.textContent = "Run desk"; }
});

// -- risk tab -------------------------------------------------------------------
$("risk-run").addEventListener("click", async () => {
  $("risk-error").textContent = "";
  try {
    const r = await api("POST", "/api/risk/evaluate", {
      orders: JSON.parse($("risk-orders-json").value),
      limits: JSON.parse($("risk-limits-json").value),
      equity: parseFloat($("risk-equity").value) || 100000,
    });
    $("risk-approved").innerHTML = table(r.approved,
      [["symbol","symbol"],["side","side"],["quantity","qty"],["price","price"]]);
    $("risk-vetoed").innerHTML = table(r.vetoed.map((v) => ({...v.order, limit: v.limit, reason: v.reason})),
      [["symbol","symbol"],["side","side"],["quantity","qty"],["limit","limit"],["reason","reason"]]);
  } catch (e) { $("risk-error").textContent = e.message; }
});

async function loadRiskLimits() {
  try {
    const limits = await api("GET", "/api/risk/limits");
    $("risk-limits").innerHTML = table(limits,
      [["name","name"],["description","description"],["params","params"]]);
  } catch (e) { $("risk-limits").innerHTML = `<span class="hint">${esc(e.message)}</span>`; }
}

// -- boot ------------------------------------------------------------------------
(async function init() {
  try { await loadSources(); } catch (e) { /* offline demo still fine */ }
  try { await loadStrategies(); } catch (e) { $("strat-list").innerHTML = `<span class="hint">${esc(e.message)}</span>`; }
  loadRiskLimits();
})();
