"""Dependency-free web server (stdlib ``http.server``).

JSON API:
    GET  /api/health
    GET  /api/sources
    GET  /api/strategies
    GET  /api/bars?symbol=SPY&source=demo&days=365
    POST /api/backtest   {strategy, symbols[], params{}, source, initial_cash}
    POST /api/desk       {symbols[], equity, source}
    GET  /api/risk/limits
    POST /api/risk/evaluate  {orders[], limits[[name, params]], equity}
    GET  /api/paper/status?config=paper-config.json
    GET  /api/paper/approvals?config=&status=pending
    POST /api/paper/approve  {config, id, reason}
    GET  /api/paper/fidelity?config=paper-config.json
    POST /api/research/pairs        {symbols[], source, days, lookback, max_pairs}
    POST /api/research/orderbook    {symbol, side, quantity, order_type, levels}
    POST /api/research/optimize     {symbols[], source, days, method, max_weight}
    POST /api/research/montecarlo   {symbols[], weights[], source, days, equity, paths, steps, seed}
    POST /api/research/factors      {symbols[], source, days, model, months}
    POST /api/research/sentiment     {symbol, source, days}
    POST /api/research/volsurface   {symbol, spot, risk_free}

The single-page UI is served from ``web/static/``.
"""

from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .. import __version__
from ..engine import (
    DataService,
    describe_limits,
    evaluate_orders_job,
    list_strategies,
    paper_approvals,
    paper_approve,
    paper_available,
    paper_fidelity,
    paper_status,
    run_backtest_job,
    run_desk_job,
    run_factor_analysis_job,
    run_montecarlo_job,
    run_optimize_job,
    run_orderbook_job,
    run_pairs_job,
    run_sentiment_price_job,
    run_vol_surface_job,
)

STATIC_DIR = Path(__file__).parent / "static"


class _Handler(BaseHTTPRequestHandler):
    data_service: DataService = DataService()

    # -- helpers ---------------------------------------------------------
    def _json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, message: str, status: int = 400) -> None:
        self._json({"error": message}, status=status)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON body: {exc}") from exc

    def log_message(self, fmt, *args):  # quieter logs
        pass

    # -- routing ----------------------------------------------------------
    def do_GET(self):
        parsed = urlparse(self.path)
        path, query = parsed.path, parse_qs(parsed.query)
        try:
            if path == "/api/health":
                return self._json({"ok": True, "version": __version__})
            if path == "/api/sources":
                return self._json(self.data_service.sources())
            if path == "/api/strategies":
                return self._json(list_strategies())
            if path == "/api/bars":
                bars = self.data_service.get_bars(
                    query.get("symbol", [""])[0],
                    source=query.get("source", ["demo"])[0],
                    days=int(query.get("days", ["365"])[0]),
                )
                return self._json({"symbol": query["symbol"][0].upper(), "bars": bars})
            if path == "/api/risk/limits":
                return self._json(describe_limits())
            if path == "/api/paper/status":
                return self._json(paper_status(query.get("config", [""])[0]))
            if path == "/api/paper/approvals":
                return self._json(paper_approvals(
                    query.get("config", [""])[0],
                    status=query.get("status", ["pending"])[0]))
            if path == "/api/paper/fidelity":
                return self._json(paper_fidelity(query.get("config", [""])[0]))
            return self._serve_static(path)
        except (ValueError, KeyError, RuntimeError) as exc:
            return self._error(str(exc), 400)
        except Exception as exc:  # pragma: no cover - defensive
            return self._error(f"internal error: {exc}", 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            body = self._read_json()
            if path == "/api/backtest":
                return self._json(self._backtest(body))
            if path == "/api/desk":
                return self._json(self._desk(body))
            if path == "/api/risk/evaluate":
                return self._json(
                    evaluate_orders_job(
                        body.get("orders", []),
                        limits=body.get("limits"),
                        equity=float(body.get("equity", 100_000.0)),
                    )
                )
            if path == "/api/paper/approve":
                return self._json(paper_approve(
                    body.get("config", ""),
                    int(body.get("id", 0)),
                    reason=body.get("reason", "")))
            if path.startswith("/api/research/"):
                return self._json(self._research(path.rsplit("/", 1)[1], body))
            return self._error(f"unknown endpoint {path}", 404)
        except (ValueError, KeyError, RuntimeError) as exc:
            return self._error(str(exc), 400)
        except Exception as exc:  # pragma: no cover - defensive
            return self._error(f"internal error: {exc}", 500)

    # -- endpoints ---------------------------------------------------------
    def _backtest(self, body: dict) -> dict:
        symbols = [s.strip().upper() for s in body.get("symbols", []) if s.strip()]
        source = body.get("source", "demo")
        bars: list = []
        for symbol in symbols:
            bars.extend(
                self.data_service.get_bars(
                    symbol, source=source, days=int(body.get("days", 365))
                )
            )
        return run_backtest_job(
            body.get("strategy", ""),
            symbols,
            body.get("params") or {},
            bars,
            initial_cash=float(body.get("initial_cash", 100_000.0)),
        )

    def _desk(self, body: dict) -> dict:
        symbols = [s.strip().upper() for s in body.get("symbols", []) if s.strip()]
        source = body.get("source", "demo")
        bars_by_symbol = {
            s: self.data_service.get_bars(s, source=source, days=int(body.get("days", 365)))
            for s in symbols
        }
        return run_desk_job(
            symbols, bars_by_symbol, equity=float(body.get("equity", 100_000.0))
        )

    def _bars_many(self, body: dict, default_days: int = 365) -> tuple[list[str], dict[str, list]]:
        symbols = [s.strip().upper() for s in body.get("symbols", []) if s.strip()]
        source = body.get("source", "demo")
        days = int(body.get("days", default_days))
        return symbols, {
            s: self.data_service.get_bars(s, source=source, days=days)
            for s in symbols
        }

    def _research(self, name: str, body: dict) -> dict:
        if name == "pairs":
            symbols, bars = self._bars_many(body)
            return run_pairs_job(symbols, bars,
                                 lookback=int(body.get("lookback", 252)),
                                 max_pairs=int(body.get("max_pairs", 10)))
        if name == "orderbook":
            return run_orderbook_job(
                symbol=body.get("symbol", "DEMO"), side=body.get("side", "buy"),
                quantity=float(body.get("quantity", 100.0)),
                order_type=body.get("order_type", "market"),
                n_levels=int(body.get("levels", 5)))
        if name == "optimize":
            symbols, bars = self._bars_many(body)
            return run_optimize_job(symbols, bars,
                                    method=body.get("method", "max_sharpe"),
                                    max_weight=float(body.get("max_weight", 1.0)))
        if name == "montecarlo":
            symbols, bars = self._bars_many(body)
            weights = body.get("weights") or None
            return run_montecarlo_job(
                symbols, bars,
                weights=[float(w) for w in weights] if weights else None,
                equity=float(body.get("equity", 100_000.0)),
                n_paths=int(body.get("paths", 5_000)),
                n_steps=int(body.get("steps", 252)),
                seed=int(body.get("seed", 7)))
        if name == "factors":
            symbols, bars = self._bars_many(body, default_days=750)
            return run_factor_analysis_job(
                symbols, bars, model=body.get("model", "ff5"),
                n_months=int(body.get("months", 60)))
        if name == "sentiment":
            symbol = (body.get("symbol") or "").strip().upper()
            return run_sentiment_price_job(
                symbol, days=int(body.get("days", 180)))
        if name == "volsurface":
            return run_vol_surface_job(
                symbol=body.get("symbol", "SPY"),
                spot=body.get("spot"),
                risk_free=float(body.get("risk_free", 0.03)))
        raise KeyError(f"unknown research job {name!r}")

    # -- static files -------------------------------------------------------
    def _serve_static(self, path: str):
        if path in ("/", ""):
            rel = "index.html"
        elif path.startswith("/static/"):
            rel = path[len("/static/"):]
        else:
            return self._error("not found", 404)
        target = (STATIC_DIR / rel).resolve()
        if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.is_file():
            return self._error("not found", 404)
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def create_server(host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), _Handler)


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = create_server(host, port)
    print(f"trade-dashboard-web v{__version__} on http://{host}:{port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
