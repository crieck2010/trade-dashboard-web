# trade-dashboard-web

The web dashboard for the [trade-suite](https://github.com/crieck2010/trade-suite):
a **Backtest Lab**, strategy catalog, agent-desk runner, risk-review
console, and market-data viewer — in one dependency-free package.

**Zero dependencies.** The server is stdlib `http.server`; the UI is
vanilla HTML/CSS/JS with inline SVG charts (no CDN, no build step, works
offline). Sibling engines (`trade-data-*`, `trade-strategies`,
`trade-backtest`, `trade-risk`, `trade-agents`) are imported lazily and
only when their tab is used.

> Research and backtesting only. Not investment advice, and it never
> trades live.

## Quick start

```bash
pip install git+https://github.com/crieck2010/trade-dashboard-web.git

# with the sibling engines on the path (or pip-installed):
python -m trade_dashboard_web --port 8000
# open http://127.0.0.1:8000
```

With no siblings installed, everything still runs against the built-in
synthetic demo data source.

## Tabs

| Tab | What it does |
|---|---|
| **Backtest Lab** | Pick a strategy + symbols + params, run a backtest, see the equity curve, metrics, and trade list |
| **Strategies** | Browse the `trade-strategies` registry: family, description, parameters |
| **Agent Desk** | Run the `trade-agents` desk over your symbols: briefs, ideas, allocations, risk vetoes |
| **Risk** | List `trade-risk` limits and evaluate your own orders against a limit stack (cumulative fills) |
| **Paper** | Paper-trading monitor (needs the `trade-paper` engine): account/equity, positions, recent orders, strategy-approval queue with approve button, backtest-vs-paper fidelity, plus a broker-reconcile demo panel (paper ledger vs read-only mock broker) |
| **Data** | Fetch bars (demo or delayed equities via `trade-data-equities`) and view a candlestick chart |
| **Live** | Demo price stream (needs `trade-stream`): latest prices per symbol from the seeded simulated feed, refreshed every 2s — DEMO STREAM, not real data |
| **Research Lab** | Ten quant-engine panels: pairs screening, order-book simulation, portfolio optimization, Monte Carlo VaR, vol-surface fitting, factor analysis, sentiment-vs-price, correlation/EDA, market breadth, macro (copper/gold) — plain-data results rendered as tables/metrics/charts |

## JSON API

```
GET  /api/health
GET  /api/sources
GET  /api/strategies
GET  /api/bars?symbol=SPY&source=demo&days=365
POST /api/backtest        {"strategy","symbols[]","params{}","source","days","initial_cash"}
POST /api/desk            {"symbols[]","equity","source","days"}
GET  /api/risk/limits
POST /api/risk/evaluate   {"orders[]","limits[[name,params]]","equity"}
GET  /api/paper/status?config=paper-config.json
GET  /api/paper/approvals?config=&status=pending
POST /api/paper/approve   {"config","id","reason"}
GET  /api/paper/fidelity?config=paper-config.json
POST /api/research/pairs        {"symbols[]","source","days","lookback","max_pairs"}
POST /api/research/orderbook    {"symbol","side","quantity","order_type","levels"}
POST /api/research/optimize     {"symbols[]","source","days","method","max_weight"}
POST /api/research/montecarlo   {"symbols[]","weights[]","source","days","equity","paths","steps","seed"}
POST /api/research/volsurface   {"symbol","spot","risk_free"}
POST /api/research/factors      {"symbols[]","source","days","model","months"}
POST /api/research/sentiment-price  {"symbol","days"}
POST /api/research/correlation     {"symbols[]","source","days","method","shrinkage","lookback"}
POST /api/research/breadth         {"preset","seed","days","thrust_window"}
POST /api/research/macro           {"preset","seed","days"}
POST /api/research/reconcile-demo  {}   (demo only: mock MCP broker)
GET  /api/stream/latest            latest demo-stream prices per symbol
```

Example:

```bash
curl -X POST localhost:8000/api/backtest \
  -d '{"strategy":"sma_crossover","symbols":["SPY"],"params":{"fast":10,"slow":50},"source":"demo"}'
```

## Architecture

Engine/UI split, per the trade-suite methodology:

```
src/trade_dashboard_web/
  engine/            # pure logic, zero web imports
    data_service.py      # demo + trade-data-equities bars, normalized to dicts
    strategy_service.py  # trade-strategies catalog
    backtest_service.py  # run backtests -> metrics, equity curve, trades
    desk_service.py      # run the agent desk -> report dict
    risk_service.py      # evaluate orders against limit stacks
    research_service.py  # research/stream/reconcile jobs, one per engine (plain in/out)
  web/
    server.py        # thin stdlib-HTTP layer: routing + JSON API + static files
    static/          # index.html, styles.css, app.js (vanilla JS, SVG charts)
  __main__.py        # python -m trade_dashboard_web
```

The engine modules are independently importable and testable without
starting the server; the web layer is a thin translation to HTTP.

Interoperability: `engine/research_service.py` is the canonical
implementation of the research jobs. The `trade-suite` meta-package's
research workflows delegate to these same `run_*_job` functions, and the
desktop dashboard binds its service names to this module whenever the web
package is installed — so a CLI run, a scripted run, the web dashboard, and
the desktop dashboard all execute the identical code path.

## Scaling notes

- `ThreadingHTTPServer` handles concurrent requests; backtest, desk, and
  Monte Carlo runs are CPU-bound and run inline — for heavy use, put a
  reverse proxy in front and/or move long runs to a task queue.
- Engine functions take plain data and return plain data, so they can be
  reused from scripts, notebooks, or the desktop dashboard unchanged.

## Limitations

- The demo data source is synthetic; validate ideas on real (even
  delayed) data before trusting them.
- The equities source needs `trade-data-equities` and `yfinance`
  installed; without them the dashboard falls back to demo data.
- Research Lab demo caveats: the vol-surface fitter runs on the engine's
  synthetic quote set (real chains plug in via `from_option_chain`);
  factor regressions run on synthetic monthly factors whose date labels
  are synthetic (real factors via `load_french_csv`); sentiment-vs-price
  uses synthetic data with a planted 1-day sentiment lead (real rows via
  archived trade-sentiment scans, which are snapshot-based). The factors
  panel needs ≥24 monthly returns per symbol (up to 750 demo bars). The
  breadth and macro panels run on seeded synthetic demo data (a 60-symbol
  universe and a copper/gold series, respectively) — illustrative only.
  The Live tab shows a simulated tick stream (AAA/BBB/CCC); reconcile-demo
  diffs the demo paper ledger against a scripted mock broker — neither
  touches real money or real prices.
- Single-process server: fine for personal research, not a production
  deployment target.

## Changelog

See [CHANGELOG.md](CHANGELOG.md). Current version: **0.4.0**.

## The maths

**What you learn.** The dashboard is a thin UI over a pure-Python engine layer: every tab and every Research Lab panel reduces to one `run_*_job` function that takes plain data in and returns plain data out. The maths lives in those jobs — backtest performance metrics, portfolio construction, and Monte Carlo risk — computed by sibling quant engines and summarized for display.

**Why it matters.** Because the engine functions are the *canonical* implementations shared with the `trade-suite` CLI workflows and the desktop dashboard, a number you see in the browser is bit-for-bit the number a scripted run produces. There is exactly one code path per computation, so "the dashboard said X" and "the CLI said X" can never disagree.

**The maths.** The Backtest Lab passes bars through `trade-backtest` and reports its metrics: total/annualized return, volatility, Sharpe ratio (`mean excess return / stdev`), max drawdown (worst peak-to-trough equity loss), and win rate. The Optimize panel builds the sample mean vector `μ` and covariance `Σ` from daily simple returns, then finds max-Sharpe (`(wᵀμ) / √(wᵀΣw)`) or minimum-variance portfolios under a max-weight cap. The Monte Carlo panel estimates per-asset `μ`, `σ`, and the correlation matrix from sample moments of simple returns, simulates correlated GBM paths (`dS = μS·dt + σS·dW`, Cholesky-correlated shocks), and reports VaR/CVaR at the chosen confidence level over the simulated terminal portfolio values. The remaining panels (pairs ADF cointegration tests, order-book impact, vol-surface SVI-style fitting, Fama-French regressions with GRS, sentiment lead-lag, Ledoit-Wolf correlation shrinkage) delegate to their engines of record and the dashboard only renders the returned plain-data results.

**Honest limitations.** The dashboard computes no statistics of its own beyond thin aggregations — its correctness inherits the sibling engines' assumptions (e.g. GBM for VaR, sample moments for the frontier). Monte Carlo and backtest jobs run inline in the request thread, so heavy runs block the single-process server. Demo-mode numbers are synthetic; the Research Lab panels carry their own demo-data caveats (synthetic vol quotes, synthetic factor dates, planted sentiment lead).
