# Architecture

## What this repo is

`trade-dashboard-web` is the **browser dashboard** of the trade-suite
system: a dependency-light (stdlib + browser) web UI over the quant
engine collection. It owns **no trading logic** — engines are the single
engine of record; this repo owns services, HTTP routes, and presentation.

```
┌────────────────────────────────────────────────────────────────────┐
│ trade-dashboard-web                                                │
│                                                                    │
│  web/server.py           stdlib HTTP server (no web framework)     │
│    GET  /                dashboard shell (index.html)              │
│    GET  /static/*        vanilla JS (app.js), no build step        │
│    POST /api/backtest    {strategy, symbols, params, source}       │
│    POST /api/strategies  strategy catalog                         │
│    POST /api/desk        agent-desk run                            │
│    POST /api/risk/...    risk review                               │
│    POST /api/paper/...   paper-trading monitor                     │
│    POST /api/research/*  seven quant-engine jobs (see below)       │
│                                                                    │
│  engine/                 pure-logic service layer                   │
│    research_service.py   canonical research jobs — the single      │
│                          source of truth consumed by trade-suite    │
│                          (CLI + pipelines) and the desktop fallback │
│  web/static/app.js       thin UI: tabs, forms, tables, charts       │
│                                                                    │
├────────────────────────────────────────────────────────────────────┤
│ engines (each the single engine of record, lazy-imported)          │
│  trade-data-* / trade-strategies / trade-backtest / trade-risk /   │
│  trade-agents / trade-paper / trade-sentiment                      │
│  research lab: trade-pairs · trade-orderbook · trade-optimize ·    │
│  trade-montecarlo · trade-volsurface · trade-factors ·             │
│  trade-sentiment-vs-price                                          │
└────────────────────────────────────────────────────────────────────┘
```

## Engine/UI split

- `engine/` has **zero browser/HTTP imports**: plain-data functions that
  are importable and testable without the server running.
- `web/` is a thin adapter: it validates request bodies, fetches bars,
  calls engine services, and serializes the result to JSON.
- The desktop dashboard (`trade-dashboard-desktop`) reuses
  `trade_dashboard_web.engine` when installed; otherwise it falls back to
  its own stdlib-only mirror with **identical function names and
  signatures** (`USING_SHARED_ENGINE` flags which is active). This keeps
  one contract with two deployments: hosted web and standalone desktop.

## The research-lab pattern (0.2.0)

Each of the seven quant engines is exposed the same way:

1. One canonical job in `engine/research_service.py`, e.g.
   `run_pairs_job(symbols, bars_by_symbol, ...)`.
2. The job **imports its engine of record directly** (lazy, with a
   `pip install git+https://github.com/crieck2010/<repo>.git` hint when
   absent) — never reimplemented here.
3. One thin POST route in `web/server.py`, e.g.
   `POST /api/research/pairs`, which fetches bars via the existing
   `DataService` and delegates to the job.
4. One vanilla-JS panel in `web/static/app.js` under the single
   **Research Lab** top-level tab, rendering the plain-data result as
   tables/metrics text.

Endpoints (canonical):

| Route | Engine |
|---|---|
| `POST /api/research/pairs` | trade-pairs |
| `POST /api/research/orderbook` | trade-orderbook |
| `POST /api/research/optimize` | trade-optimize |
| `POST /api/research/montecarlo` | trade-montecarlo |
| `POST /api/research/volsurface` | trade-volsurface |
| `POST /api/research/factors` | trade-factors |
| `POST /api/research/sentiment-price` | trade-sentiment-vs-price |

`/api/research/sentiment` is kept as a compatibility alias for
`sentiment-price`.

## Interoperability notes

- **Contract is plain data in / plain data out.** Every research job
  takes dicts/lists and returns JSON-serializable dicts, so the web
  server, the desktop tab, and the `trade-suite` CLI produce
  byte-comparable results for the same inputs.
- **Engines stay optional.** Missing engines raise a `RuntimeError` with
  an install hint (HTTP 400), never a 500, and the UI degrades to an
  inline error.
- **Cross-consumer agreement.** `trade-suite`'s research workflows
  delegate to these same jobs, so `trade-suite pairs` and the dashboard's
  Pairs panel run identical code.

## Scaling notes

- The server runs research jobs **inline on the request thread** — fine
  for demo-scale workloads, but CPU-heavy jobs (large Monte Carlo path
  counts, wide pair screens) block the single-threaded server.
- A heavier deployment would put a task queue / worker process between
  `web/server.py` and `engine/research_service.py`; the jobs already have
  the right shape for that (pure functions, no server state).
- Factor analysis needs ≥ 24 monthly returns per symbol; the endpoint
  requests up to 750 days of bars (the demo cap) to reach that floor.
