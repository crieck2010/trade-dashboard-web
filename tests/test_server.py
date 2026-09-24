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


# -- research lab endpoints ----------------------------------------------------

def _post_research(base_url, name, payload):
    pytest.importorskip("trade_pairs" if name == "pairs" else
                        "trade_orderbook" if name == "orderbook" else
                        "trade_optimize" if name == "optimize" else
                        "trade_montecarlo" if name == "montecarlo" else
                        "trade_volsurface" if name == "volsurface" else
                        "trade_factors" if name == "factors" else
                        "trade_eda" if name == "correlation" else
                        "trade_breadth" if name == "breadth" else
                        "trade_macro" if name == "macro" else
                        "trade_paper" if name == "reconcile-demo" else
                        "trade_sentiment_vs_price")
    return post(base_url, f"/api/research/{name}", payload)


def test_research_pairs_endpoint(base_url):
    status, data = _post_research(base_url, "pairs", {
        "symbols": ["SPY", "QQQ", "IWM"], "source": "demo", "days": 200,
        "lookback": 100, "max_pairs": 3})
    assert status == 200 and data["source"] == "trade-pairs"


def test_research_orderbook_endpoint(base_url):
    status, data = _post_research(base_url, "orderbook",
                                  {"side": "sell", "quantity": 50, "order_type": "market", "levels": 5})
    assert status == 200 and data["source"] == "trade-orderbook"


def test_research_optimize_endpoint(base_url):
    status, data = _post_research(base_url, "optimize", {
        "symbols": ["SPY", "QQQ"], "source": "demo", "days": 200, "method": "equal_weight"})
    assert status == 200 and data["source"] == "trade-optimize"


def test_research_montecarlo_endpoint(base_url):
    status, data = _post_research(base_url, "montecarlo", {
        "symbols": ["SPY", "QQQ"], "source": "demo", "days": 200,
        "equity": 100000, "paths": 200, "steps": 60, "seed": 7})
    assert status == 200 and data["source"] == "trade-montecarlo"


def test_research_volsurface_endpoint(base_url):
    status, data = _post_research(base_url, "volsurface", {"symbol": "SPY"})
    assert status == 200 and data["source"] == "trade-volsurface"


def test_research_factors_endpoint(base_url):
    status, data = _post_research(base_url, "factors", {
        "symbols": ["SPY", "QQQ"], "source": "demo", "model": "ff3", "months": 24})
    assert status == 200 and data["source"] == "trade-factors"


def test_research_sentiment_endpoint(base_url):
    status, data = _post_research(base_url, "sentiment-price", {"symbol": "SPY"})
    assert status == 200 and data["source"] == "trade-sentiment-vs-price"


def test_research_sentiment_alias_endpoint(base_url):
    status, data = _post_research(base_url, "sentiment", {"symbol": "SPY"})
    assert status == 200 and data["source"] == "trade-sentiment-vs-price"


def test_research_correlation_endpoint(base_url):
    status, data = _post_research(base_url, "correlation", {
        "symbols": ["SPY", "QQQ", "IWM"], "source": "demo", "days": 200,
        "method": "pearson", "lookback": 100})
    assert status == 200 and data["source"] == "trade-eda"
    assert len(data["correlation"]["matrix"]) == 3
    assert data["n_obs"] == 99


def test_research_index_has_tab(base_url):
    import urllib.request
    with urllib.request.urlopen(base_url + "/") as res:
        html = res.read().decode()
    assert "Research Lab" in html and "rs-pairs-run" in html


def test_research_breadth_endpoint(base_url):
    status, data = _post_research(base_url, "breadth", {
        "seed": 7, "days": 300, "thrust_window": 10})
    assert status == 200 and data["source"] == "trade-breadth"
    assert data["snapshot"]["regime"]
    assert 0.0 <= data["snapshot"]["fragility"] <= 1.0


def test_research_macro_endpoint(base_url):
    status, data = _post_research(base_url, "macro",
                                 {"seed": 42, "days": 300})
    assert status == 200 and data["source"] == "trade-macro"
    assert data["snapshot"]["z_score"] is not None
    assert "ratio_vs_200dma" in data["snapshot"]


def test_research_reconcile_demo_endpoint(base_url):
    status, data = _post_research(base_url, "reconcile-demo", {})
    assert status == 200 and data["source"] == "trade-paper"
    assert data["demo"] is True
    assert data["reconcile"]["clean"] is False  # deliberate drift


def test_stream_latest_endpoint(base_url):
    pytest.importorskip("trade_stream")
    status, data = get(base_url, "/api/stream/latest")
    assert status == 200 and data["demo"] is True
    assert data["source"] == "trade-stream"
    assert set(data["symbols"]) == {"AAA", "BBB", "CCC"}
    assert data["prices"]  # first batch lands within ~2s of session start


def test_research_breadth_bad_preset(base_url):
    pytest.importorskip("trade_breadth")
    status, data = post(base_url, "/api/research/breadth",
                        {"preset": "bogus", "days": 300})
    assert status == 400 and "error" in data


def test_stream_latest_missing_engine(base_url):
    import sys
    if "trade_stream" in sys.modules:
        pytest.skip("trade_stream present; missing-engine path not exercised")
    status, data = get(base_url, "/api/stream/latest")
    assert status == 400 and "trade-stream" in data["error"]


def test_reconcile_demo_missing_engine(base_url):
    import sys
    if "trade_paper" in sys.modules:
        pytest.skip("trade_paper present; missing-engine path not exercised")
    status, data = post(base_url, "/api/research/reconcile-demo", {})
    assert status == 400 and "trade-paper" in data["error"]
