"""Live-server tests over real HTTP (stdlib http.client)."""

from __future__ import annotations

import json
import threading
import urllib.request

import pytest

from trade_dashboard_web.web import create_server


@pytest.fixture(scope="module")
def base_url():
    server = create_server("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    yield f"http://{host}:{port}"
    server.shutdown()
    thread.join()


def get(base_url, path):
    try:
        with urllib.request.urlopen(base_url + path) as res:
            return res.status, json.loads(res.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def post(base_url, path, payload):
    req = urllib.request.Request(
        base_url + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as res:
            return res.status, json.loads(res.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_health(base_url):
    status, data = get(base_url, "/api/health")
    assert status == 200 and data["ok"] is True


def test_index_served(base_url):
    with urllib.request.urlopen(base_url + "/") as res:
        html = res.read().decode()
    assert "trade-dashboard-web" in html
    assert res.headers.get_content_type() == "text/html"


def test_static_js_served(base_url):
    with urllib.request.urlopen(base_url + "/static/app.js") as res:
        assert b"fetch" in res.read()


def test_bars_endpoint(base_url):
    status, data = get(base_url, "/api/bars?symbol=SPY&source=demo&days=100")
    assert status == 200 and len(data["bars"]) == 100


def test_bars_endpoint_bad_symbol(base_url):
    status, data = get(base_url, "/api/bars?symbol=&source=demo")
    assert status == 400 and "error" in data


def test_backtest_endpoint(base_url):
    pytest.importorskip("trade_strategies")
    status, data = post(base_url, "/api/backtest", {
        "strategy": "sma_crossover",
        "symbols": ["SPY"],
        "params": {"fast": 10, "slow": 30},
        "source": "demo",
        "days": 200,
        "initial_cash": 100000,
    })
    assert status == 200
    assert data["final_equity"] > 0
    assert len(data["equity_curve"]) == 200


def test_desk_endpoint(base_url):
    pytest.importorskip("trade_agents")
    status, data = post(base_url, "/api/desk", {
        "symbols": ["SPY", "AAPL"],
        "equity": 100000,
        "source": "demo",
        "days": 200,
    })
    assert status == 200
    assert "briefs" in data


def test_risk_evaluate_endpoint(base_url):
    pytest.importorskip("trade_risk")
    status, data = post(base_url, "/api/risk/evaluate", {
        "orders": [{"symbol": "SPY", "side": "LONG", "quantity": 10, "price": 100.0}],
        "limits": [["max_position_notional", {"max_pct": 0.25}]],
        "equity": 100000,
    })
    assert status == 200 and len(data["approved"]) == 1


def test_unknown_endpoint(base_url):
    status, _ = post(base_url, "/api/nope", {})
    assert status == 404
