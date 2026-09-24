"use strict";
// Minimal vanilla-JS client. No dependencies, no build step.

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const fmtMoney = (v) => "$" + (+v).toLocaleString("en-US", {minimumFractionDigits: 2, maximumFractionDigits: 2});

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
  for (const id of ["bt-source", "desk-source", "data-source",
                    "rs-pairs-source", "rs-opt-source", "rs-mc-source", "rs-fa-source",
                    "rs-co-source"]) {
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

// -- paper tab ------------------------------------------------------------------
async function loadPaper() {
  $("paper-error").textContent = "";
  $("paper-missing").hidden = true;
  const cfg = $("paper-config").value.trim();
  const q = `?config=${encodeURIComponent(cfg)}`;
  try {
    const s = await api("GET", "/api/paper/status" + q);
    $("paper-account").innerHTML =
      `equity <b>${esc(fmtMoney(s.equity))}</b> · cash ${esc(fmtMoney(s.cash))} · ` +
      `buying power ${esc(fmtMoney(s.buying_power))} · broker ${esc(s.broker)} · ` +
      `${s.market_open ? "market OPEN" : "market closed"} · ` +
      `${s.active_strategies} active strateg${s.active_strategies === 1 ? "y" : "ies"} · ` +
      `${s.pending_approvals} awaiting approval`;
    $("paper-positions").innerHTML = table(s.positions,
      [["symbol","symbol"],["qty","qty"],["avg_entry","entry"],["market","mark"],["unrealized","uPnL"],["asset_class","class"]]);
    $("paper-orders").innerHTML = table(s.recent_orders,
      [["symbol","symbol"],["side","side"],["qty","qty"],["strategy","strategy"],["state","state"]]);
  } catch (e) {
    if (e.message.includes("trade-paper is not installed")) { $("paper-missing").hidden = false; return; }
    $("paper-error").textContent = e.message; return;
  }
  try {
    const a = await api("GET", "/api/paper/approvals" + q + "&status=pending");
    $("paper-approvals").innerHTML = a.approvals.length ? a.approvals.map((r) => {
      const m = r.metrics || {};
      return `<div class="brief"><b>#${r.id} ${esc(r.strategy)}</b> <span class="hint">${esc(r.symbols)}` +
        ` · score=${(+r.score || 0).toFixed(2)}` +
        ` · sharpe=${((m.sharpe_ratio || 0)).toFixed(2)}` +
        ` · dd=${(((m.max_drawdown || 0)) * 100).toFixed(1)}%</span> ` +
        `<button data-approve="${r.id}">Approve</button></div>`;
    }).join("") : `<span class="hint">queue empty — new discoveries arrive after each 3×-daily cycle</span>`;
    $("paper-approvals").querySelectorAll("[data-approve]").forEach((btn) =>
      btn.addEventListener("click", async () => {
        try {
          await api("POST", "/api/paper/approve", {config: cfg, id: +btn.dataset.approve, reason: "approved from dashboard"});
          loadPaper();
        } catch (e) { $("paper-error").textContent = e.message; }
      }));
  } catch (e) { $("paper-error").textContent = e.message; }
  try {
    const f = await api("GET", "/api/paper/fidelity" + q);
    const rows = Object.entries(f.strategies || {}).map(([strategy, s]) => ({
      strategy, fills: s.fills,
      avg_realized_bps: s.avg_realized_slippage_bps == null ? "n/a" : s.avg_realized_slippage_bps,
      gap_bps: s.slippage_gap_bps == null ? "n/a" : s.slippage_gap_bps,
      verdict: s.verdict,
    }));
    $("paper-fidelity").innerHTML =
      `<div class="hint">backtest assumption: ${f.assumed_slippage_bps} bps · ${f.total_fills} fills</div>` +
      (rows.length ? table(rows, [["strategy","strategy"],["fills","fills"],["avg_realized_bps","avg bps"],["gap_bps","gap bps"],["verdict","verdict"]])
                   : `<span class="hint">no fills recorded yet</span>`);
  } catch (e) { $("paper-error").textContent = e.message; }
}

$("paper-refresh").addEventListener("click", loadPaper);
document.querySelector('[data-tab="paper"]').addEventListener("click", loadPaper);

// -- boot ------------------------------------------------------------------------
(async function init() {
  try { await loadSources(); } catch (e) { /* offline demo still fine */ }
  try { await loadStrategies(); } catch (e) { $("strat-list").innerHTML = `<span class="hint">${esc(e.message)}</span>`; }
  loadRiskLimits();
})();

// -- research lab --------------------------------------------------------------
document.querySelectorAll("#research-tabs button").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("#research-tabs button").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".rsub").forEach((t) => t.classList.remove("active"));
    btn.classList.add("active");
    $("rsub-" + btn.dataset.rsub).classList.add("active");
  });
});
const rSyms = (id) => $(id).value.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean);
const rMetrics = (el, obj) => { $(el).innerHTML = Object.entries(obj).map(
  ([k, v]) => `<div class="metric"><span>${esc(k)}</span><b>${esc(fmtCell(v))}</b></div>`).join(""); };
async function rRun(btn, errorId, fn) {
  const b = $(btn); b.disabled = true; $(errorId).textContent = "";
  try { await fn(); } catch (e) { $(errorId).textContent = e.message; }
  b.disabled = false;
}

$("rs-pairs-run").addEventListener("click", () => rRun("rs-pairs-run", "rs-pairs-error", async () => {
  const r = await api("POST", "/api/research/pairs", {
    symbols: rSyms("rs-pairs-symbols"), source: $("rs-pairs-source").value,
    lookback: +$("rs-pairs-lookback").value, max_pairs: 10});
  $("rs-pairs-table").innerHTML = table(r.pairs.map((p) => ({
    pair: `${p.symbol_a} / ${p.symbol_b}`, verdict: p.cointegrated ? "cointegrated" : "not",
    adf_stat: p.adf.stat.toFixed(2), beta: p.hedge_ratio.toFixed(3),
    half_life: p.half_life_bars == null ? "n/a" : p.half_life_bars.toFixed(1),
  })), [["pair","pair"],["verdict","verdict"],["adf_stat","ADF stat"],["beta","beta"],["half_life","half-life bars"]]);
}));

$("rs-ob-run").addEventListener("click", () => rRun("rs-ob-run", "rs-ob-error", async () => {
  const r = await api("POST", "/api/research/orderbook", {
    symbol: "DEMO", side: $("rs-ob-side").value, quantity: +$("rs-ob-qty").value,
    order_type: $("rs-ob-type").value, levels: 5});
  rMetrics("rs-ob-metrics", {filled_qty: r.filled_qty, fill_ratio: r.fill_ratio,
    avg_fill_price: r.avg_fill_price, slippage_bps: r.slippage_bps, n_fills: r.n_fills});
}));

$("rs-opt-run").addEventListener("click", () => rRun("rs-opt-run", "rs-opt-error", async () => {
  const r = await api("POST", "/api/research/optimize", {
    symbols: rSyms("rs-opt-symbols"), source: $("rs-opt-source").value,
    method: $("rs-opt-method").value, max_weight: 1.0});
  rMetrics("rs-opt-weights", {...r.weights, expected_return: r.expected_return,
    volatility: r.volatility, sharpe: r.sharpe});
  $("rs-opt-chart").innerHTML = lineChart(r.frontier.map((p) => p.expected_return));
}));

$("rs-mc-run").addEventListener("click", () => rRun("rs-mc-run", "rs-mc-error", async () => {
  const r = await api("POST", "/api/research/montecarlo", {
    symbols: rSyms("rs-mc-symbols"), source: $("rs-mc-source").value,
    equity: +$("rs-mc-equity").value, paths: +$("rs-mc-paths").value, steps: 252, seed: 7});
  rMetrics("rs-mc-metrics", {var: r.var, cvar: r.cvar, mean_pnl: r.mean_pnl,
    p_profit: r.prob_profit, median_pnl: r.median_pnl, paths: r.n_paths});
}));

$("rs-vs-run").addEventListener("click", () => rRun("rs-vs-run", "rs-vs-error", async () => {
  const r = await api("POST", "/api/research/volsurface", {symbol: $("rs-vs-symbol").value});
  const rows = Object.entries(r.svi_fits).map(([T, f]) => ({T, ...f}));
  $("rs-vs-table").innerHTML = table(rows,
    [["T","expiry T"],["a","a"],["b","b"],["rho","rho"],["m","m"],["sigma","sigma"]]);
}));

$("rs-fa-run").addEventListener("click", () => rRun("rs-fa-run", "rs-fa-error", async () => {
  const r = await api("POST", "/api/research/factors", {
    symbols: rSyms("rs-fa-symbols"), source: $("rs-fa-source").value, days: 750,
    model: $("rs-fa-model").value, months: 60});
  const g = r.grs || {};
  $("rs-fa-verdict").textContent =
    `${r.model.toUpperCase()} · ${r.n_months} months\n` +
    `GRS joint-alpha test: F=${(+g.F || 0).toFixed(2)}, p=${(+g.pvalue || 1).toFixed(4)} ` +
    ((+g.pvalue || 1) < 0.05 ? "→ reject joint zero-alpha" : "→ cannot reject joint zero-alpha");
  $("rs-fa-table").innerHTML = table(Object.entries(r.assets).map(([symbol, a]) => ({
    symbol, alpha: a.alpha.toFixed(4), alpha_t: a.alpha_t.toFixed(2),
    alpha_p: a.alpha_p.toFixed(3), r_squared: a.rsquared.toFixed(3),
    sig_5pct: a.alpha_p < 0.05 ? "yes" : "no"})),
    [["symbol","symbol"],["alpha","alpha"],["alpha_t","alpha t"],["alpha_p","alpha p"],["r_squared","R²"],["sig_5pct","sig 5%"]]);
}));

$("rs-se-run").addEventListener("click", () => rRun("rs-se-run", "rs-se-error", async () => {
  const r = await api("POST", "/api/research/sentiment-price", {symbol: $("rs-se-symbol").value});
  $("rs-se-verdict").textContent = JSON.stringify(r, null, 2);
}));

function corrHeatmap(symbols, matrix) {
  let s = "<table><tr><th></th>" + symbols.map((x) => `<th>${esc(x)}</th>`).join("") + "</tr>";
  matrix.forEach((row, i) => {
    s += `<tr><th>${esc(symbols[i])}</th>` + row.map((v) => {
      const a = Math.min(Math.abs(v) * 0.85, 0.85).toFixed(2);
      const bg = v >= 0 ? `rgba(63,208,140,${a})` : `rgba(255,107,107,${a})`;
      return `<td style="background:${bg}">${v.toFixed(2)}</td>`;
    }).join("") + "</tr>";
  });
  return s + "</table>";
}

$("rs-co-run").addEventListener("click", () => rRun("rs-co-run", "rs-co-error", async () => {
  const r = await api("POST", "/api/research/correlation", {
    symbols: rSyms("rs-co-symbols"), source: $("rs-co-source").value,
    method: $("rs-co-method").value, shrinkage: $("rs-co-shrinkage").value,
    lookback: +$("rs-co-lookback").value});
  const hi = r.diversification.max_pairwise_corr;
  rMetrics("rs-co-metrics", {
    n_symbols: r.symbols.length, n_obs: r.n_obs,
    mean_pairwise_corr: r.diversification.mean_pairwise_corr,
    max_pair: `${hi.a}/${hi.b} = ${hi.value.toFixed(3)}`,
    effective_n: r.diversification.effective_n_equal_weight,
    shrinkage_delta: r.covariance.shrinkage_delta});
  $("rs-co-matrix").innerHTML = corrHeatmap(r.symbols, r.correlation.matrix);
  $("rs-co-describe").innerHTML = table(Object.entries(r.describe).map(([s, d]) => ({
    symbol: s, n: d.n, mean_ann: d.mean_annualized, vol_ann: d.vol_annualized,
    skew: d.skew, kurt: d.kurtosis_excess, jb: d.jarque_bera})),
    [["symbol", "Symbol"], ["n", "n"], ["mean_ann", "Mean (ann)"], ["vol_ann", "Vol (ann)"],
     ["skew", "Skew"], ["kurt", "Ex. kurt"], ["jb", "JB"]]);
  $("rs-co-quality").innerHTML = table(Object.entries(r.quality).map(([s, q]) => ({
    symbol: s, n_bars: q.n_bars, missing: q.missing_closes,
    zero_vol: q.zero_volume_bars, stale: q.stale_close_runs,
    outliers: q.price_outliers_mad, clean: q.clean ? "yes" : "NO"})),
    [["symbol", "Symbol"], ["n_bars", "Bars"], ["missing", "Missing"],
     ["zero_vol", "Zero vol"], ["stale", "Stale runs"], ["outliers", "Outliers"],
     ["clean", "Clean"]]);
}));

// -- research lab: breadth --------------------------------------------------------
$("rs-br-run").addEventListener("click", () => rRun("rs-br-run", "rs-br-error", async () => {
  const r = await api("POST", "/api/research/breadth", {
    preset: $("rs-br-preset").value, seed: +$("rs-br-seed").value,
    days: +$("rs-br-days").value, thrust_window: +$("rs-br-thrust").value});
  const s = r.snapshot;
  rMetrics("rs-br-metrics", {
    regime: s.regime, regime_score: s.regime_score, date: s.date,
    n_symbols: r.n_symbols, thrust_window: (s.config || {}).thrust_window});
  const f = +s.fragility || 0;
  $("rs-br-fragility").innerHTML =
    `<div class="hint">fragility ${f.toFixed(3)} / 1.00</div>` +
    `<div style="background:#1c2333;border-radius:4px;height:12px">` +
    `<div style="width:${(f * 100).toFixed(1)}%;height:12px;border-radius:4px;background:` +
    (f > 0.66 ? "#ff6b6b" : f > 0.33 ? "#f0a24a" : "#3fd08c") + `"></div></div>`;
  $("rs-br-thrusts").innerHTML = table(s.thrusts_recent.map((t) => ({
    date: t.date, type: t.type, magnitude: t.magnitude,
    pct_above_50dma: t.pct_above_50dma, window: t.window})),
    [["date", "Date"], ["type", "Type"], ["magnitude", "Magnitude"],
     ["pct_above_50dma", "% > 50DMA"], ["window", "Window"]]);
  const ind = s.indicators || {};
  rMetrics("rs-br-indicators", {
    pct_above_50dma: ind.pct_above_50dma, pct_above_200dma: ind.pct_above_200dma,
    ad_ratio: ind.ad_ratio, mcclellan_oscillator: ind.mcclellan_oscillator,
    ew_cw_ratio: ind.ew_cw_ratio, up_down_volume_ratio: ind.up_down_volume_ratio,
    new_highs: ind.new_highs, new_lows: ind.new_lows,
    warnings: (s.warnings || []).map((w) => w.type || JSON.stringify(w)).join(", ") || "none"});
}));

// -- research lab: macro ----------------------------------------------------------
$("rs-ma-run").addEventListener("click", () => rRun("rs-ma-run", "rs-ma-error", async () => {
  const r = await api("POST", "/api/research/macro", {
    preset: $("rs-ma-preset").value, seed: +$("rs-ma-seed").value,
    days: +$("rs-ma-days").value});
  const s = r.snapshot;
  rMetrics("rs-ma-metrics", {
    regime: s.regime, date: s.date,
    z_score: s.z_score, ratio: s.ratio, ratio_vs_200dma: s.ratio_vs_200dma,
    roc_21d: s.roc_21d,
    transition_alert: s.transition_alert ? "YES — " + (s.transition && s.transition.direction) : "no"});
}));

// -- paper tab: broker reconcile (demo) -------------------------------------------
$("paper-reconcile-run").addEventListener("click", async () => {
  const b = $("paper-reconcile-run"); b.disabled = true; $("paper-reconcile-error").textContent = "";
  try {
    const r = await api("POST", "/api/research/reconcile-demo", {});
    const rc = r.reconcile;
    rMetrics("paper-reconcile-metrics", {
      clean: rc.clean ? "yes" : "NO — drift detected",
      matched: rc.matched.length, account: r.account_id});
    const rows = [];
    rc.missing_from_broker.forEach((m) => rows.push({symbol: m.symbol, side: "in paper only", paper: m.paper, broker: ""}));
    rc.missing_from_ledger.forEach((m) => rows.push({symbol: m.symbol, side: "at broker only", paper: "", broker: m.broker}));
    rc.quantity_mismatches.forEach((m) => rows.push({symbol: m.symbol, side: "qty mismatch", paper: m.paper, broker: m.broker}));
    $("paper-reconcile-table").innerHTML = table(rows,
      [["symbol", "Symbol"], ["side", "Drift"], ["paper", "Paper qty"], ["broker", "Broker qty"]]);
  } catch (e) { $("paper-reconcile-error").textContent = e.message; }
  b.disabled = false;
});

// -- live tab: demo stream ----------------------------------------------------------
let liveTimer = null;
async function loadLive() {
  try {
    const r = await api("GET", "/api/stream/latest");
    $("live-table").innerHTML = table(r.symbols.map((s) => {
      const p = r.prices[s] || {};
      return {symbol: s, price: p.price, ts: p.ts};
    }), [["symbol", "Symbol"], ["price", "Price"], ["ts", "Tick ts"]]);
  } catch (e) { $("live-error").textContent = e.message; }
}
document.querySelector('[data-tab="live"]').addEventListener("click", () => {
  loadLive();
  if (!liveTimer) {
    liveTimer = setInterval(() => {
      if ($("tab-live").classList.contains("active")) loadLive();
    }, 2000);
  }
});
