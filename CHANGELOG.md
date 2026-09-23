# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
