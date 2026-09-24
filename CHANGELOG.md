# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
