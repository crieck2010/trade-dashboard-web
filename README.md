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
| **Paper** | Paper-trading monitor (needs the `trade-paper` engine): account/equity, positions, recent orders, strategy-approval queue with approve button, backtest-vs-paper fidelity |
| **Data** | Fetch bars (demo or delayed equities via `trade-data-equities`) and view a candlestick chart |

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
  web/
    server.py        # thin stdlib-HTTP layer: routing + JSON API + static files
    static/          # index.html, styles.css, app.js (vanilla JS, SVG charts)
  __main__.py        # python -m trade_dashboard_web
```

The engine modules are independently importable and testable without
starting the server; the web layer is a thin translation to HTTP.

## Scaling notes

- `ThreadingHTTPServer` handles concurrent requests; backtest and desk
  runs are CPU-bound and run inline — for heavy use, put a reverse proxy
  in front and/or move long runs to a task queue.
- Engine functions take plain data and return plain data, so they can be
  reused from scripts, notebooks, or the desktop dashboard unchanged.

## Limitations

- The demo data source is synthetic; validate ideas on real (even
  delayed) data before trusting them.
- The equities source needs `trade-data-equities` and `yfinance`
  installed; without them the dashboard falls back to demo data.
- Single-process server: fine for personal research, not a production
  deployment target.

## Changelog

See [CHANGELOG.md](CHANGELOG.md). Current version: **0.1.0**.
