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
