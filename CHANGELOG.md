# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-09-24

### Added
- Ninth and tenth **Research Lab** panels: **Breadth** (`trade-breadth`) —
  regime badge, fragility gauge (0–1 bar), recent breadth-thrust list, and
  key indicators over a seeded 60-symbol demo universe; **Macro**
  (`trade-macro`) — regime badge, copper/gold z-score, ratio vs 200DMA,
  and transition alerts from a synthetic demo series.
- New top-level **Live** tab: latest prices per symbol from a demo
  `trade-stream` session, polled every 2s, labeled
  "DEMO STREAM — simulated feed" (not real data).
- New **Broker reconcile (demo)** panel on the Paper tab: `POST
  /api/research/reconcile-demo` diffs the deliberate-drift demo paper
  ledger against the read-only Robinhood MCP mock (`trade-paper`) and
  renders matched / missing / quantity-mismatch rows.
- `run_breadth_job`, `run_macro_job`, `run_stream_demo_job`, and
  `run_reconcile_demo_job` in `engine/research_service.py` (canonical,
  plain-data, lazy engine imports); new endpoints
  `POST /api/research/breadth` (`{preset, seed, days, thrust_window}`),
  `POST /api/research/macro` (`{preset, seed, days}`),
  `POST /api/research/reconcile-demo` (`{}`, demo only), and
  `GET /api/stream/latest` — served from a module-level lazily-started
  demo stream session (`StreamSession` `source="demo"`,
  `LatestPriceCache` on its bus; the finite demo feed is re-created with
  a fresh timestamp offset on each exhaustion so it runs indefinitely).
- 9 new tests: 4 engine research-job tests, 4 missing-engine install-hint
  tests, and live-server tests for the 3 new POST endpoints plus
  `GET /api/stream/latest`.

### Notes
- `trade-data-equities` v0.2.0's `PolygonProvider` is data-layer only
  (a new bar source inside that engine) — no dashboard code change.
- Demo caveats: breadth uses the engine's seeded 60-symbol demo universe,
  macro uses a synthetic copper/gold series; both illustrative only.
  The Live tab's ticks are simulated (AAA/BBB/CCC), not real prices.

## [0.3.0] - 2026-09-24

### Added
- Eighth **Research Lab** panel: **Correlations** (trade-eda) — Pearson/
  Spearman correlation heatmap, Ledoit-Wolf shrunk covariance, per-asset
  summary stats (vol, skew, kurtosis, Jarque-Bera), data-quality flags,
  and diversification stats (mean/max pairwise correlation, effective
  number of bets).
- `run_correlation_job` in `engine/research_service.py` (canonical,
  plain-data, lazy `trade-eda` import) and
  `POST /api/research/correlation`
  (`{symbols[], source, days, method, shrinkage, lookback}`).
- 2 new tests: engine research-job test + live-server endpoint test.

## [0.2.0] - 2026-09-24

### Added
- New **Research Lab** tab with seven sub-panels, one per new quant engine:
  **Pairs** (Engle-Granger cointegration screening, `trade-pairs`),
  **Order book** (limit-order-book simulation and fill quality, `trade-orderbook`),
  **Optimize** (Markowitz portfolio optimization + efficient frontier, `trade-optimize`),
  **Monte Carlo** (correlated-GBM portfolio VaR/CVaR, `trade-montecarlo`),
  **Vol surface** (SVI volatility-surface fitting, `trade-volsurface`),
  **Factors** (Fama-French time-series regressions + GRS test, `trade-factors`),
  **Sentiment** (sentiment-vs-price verdict bundle, `trade-sentiment-vs-price`).
- New `engine/research_service.py` with seven `run_*_job` functions: each
  talks to its engine of record directly (lazy import with an install hint),
  takes plain data in, and returns JSON-serializable data out. The
  `trade-suite` meta-package delegates its research workflows to these same
  jobs, so a scripted run and a dashboard run agree exactly.
- Seven new JSON API endpoints under `/api/research/`: `pairs`, `orderbook`,
  `optimize`, `montecarlo`, `volsurface`, `factors`, `sentiment-price`
  (`/api/research/sentiment` kept as a compatibility alias).
- 14 new tests: 7 engine research-job tests + 7 live-server endpoint tests.

### Notes
- Factor analysis needs at least 24 monthly returns per symbol, so the
  factors endpoint requests up to 750 days of bars (the demo cap).
- Demo modes: vol surface uses the engine's synthetic quote set; factor
  regressions use the engine's synthetic monthly factors (date labels are
  synthetic in demo mode, alignment is what matters); sentiment-vs-price
  uses synthetic data with a planted 1-day sentiment lead. Real data plugs
  in through the same engine adapters (`from_option_chain`,
  `load_french_csv`, archived trade-sentiment rows).

## [0.1.1] - 2026-09-23

### Added
- New **Paper** tab wired to the `trade-paper` engine (lazy optional import):
  paper account/equity/buying power, open positions, recent orders, pending
  strategy-approval queue with one-click approve, and a fidelity report
  comparing backtest slippage assumptions to realized paper slippage.
- New JSON API endpoints: `GET /api/paper/status`, `GET /api/paper/approvals`,
  `POST /api/paper/approve`, `GET /api/paper/fidelity`.
- New `engine/paper_service.py` (`paper_status`, `paper_approvals`,
  `paper_approve`, `paper_fidelity`, `paper_available`) with an install hint
  when `trade-paper` is not present.

## [0.1.0] - 2026-09-23

### Added
- Dependency-free web dashboard (stdlib `http.server` + vanilla JS, no
  build step, no CDN): Backtest Lab, strategy catalog, agent-desk runner,
  risk-review console, market-data viewer with SVG equity/candlestick charts.
- Pure-logic `engine/` package (no web imports): `DataService` (demo +
  lazy `trade-data-equities` sources, bars normalized to dicts),
  `strategy_service`, `backtest_service` (metrics, equity curve, trades),
  `desk_service`, `risk_service` (cumulative-fill order evaluation).
- JSON API: health, sources, strategies, bars, backtest, desk,
  risk limits, risk evaluation.
- `python -m trade_dashboard_web` entry point plus `trade-dashboard-web`
  console script.
- 18 tests: engine services plus live-server tests over real HTTP.
