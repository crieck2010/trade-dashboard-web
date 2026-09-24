"""Engine-service tests (no HTTP involved)."""

import pytest

from trade_dashboard_web.engine import (
    DataService,
    bar_to_dict,
    describe_limits,
    evaluate_orders_job,
    list_strategies,
    run_backtest_job,
    run_desk_job,
)


def test_demo_bars_shape():
    bars = DataService().get_bars("SPY", source="demo", days=200)
    assert len(bars) == 200
    b = bars[0]
    assert set(b) == {"symbol", "timestamp", "open", "high", "low", "close", "volume"}
    assert b["high"] >= b["low"]


def test_bar_to_dict_from_engine_bar():
    pytest.importorskip("trade_data_equities")
    from trade_data_equities.models import Bar
    from datetime import datetime, timezone

    bar = Bar(timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc), open=1, high=2, low=0.5, close=1.5, volume=10)
    d = bar_to_dict(bar)
    assert d["close"] == 1.5 and d["timestamp"].startswith("2024-01-02")


def test_sources_lists_demo():
    sources = DataService().sources()
    assert sources[0]["id"] == "demo" and sources[0]["available"]


def test_get_bars_validates():
    with pytest.raises(ValueError):
        DataService().get_bars("", source="demo")
    with pytest.raises(ValueError):
        DataService().get_bars("SPY", source="nope")


def test_list_strategies():
    pytest.importorskip("trade_strategies")
    strategies = list_strategies()
    assert len(strategies) >= 15
    names = [s["name"] for s in strategies]
    assert "sma_crossover" in names


def test_run_backtest_job(demo_bars):
    pytest.importorskip("trade_strategies")
    result = run_backtest_job("sma_crossover", ["SPY"], {"fast": 10, "slow": 30}, demo_bars)
    assert result["final_equity"] > 0
    assert "sharpe_ratio" in result["metrics"]
    assert len(result["equity_curve"]) == len(demo_bars)
    assert isinstance(result["trades"], list)


def test_run_desk_job():
    pytest.importorskip("trade_agents")
    pytest.importorskip("trade_risk")
    svc = DataService()
    bars = {s: svc.get_bars(s, source="demo", days=200) for s in ("SPY", "AAPL")}
    report = run_desk_job(["SPY", "AAPL"], bars, equity=100_000.0)
    assert "briefs" in report and "allocations" in report
    assert len(report["approved_orders"]) + len(report["vetoes"]) == len(report["allocations"])


def test_evaluate_orders_job():
    pytest.importorskip("trade_risk")
    out = evaluate_orders_job(
        [{"symbol": "SPY", "side": "LONG", "quantity": 1000, "price": 500.0}],
        limits=[["max_position_notional", {"max_pct": 0.25}]],
        equity=100_000.0,
    )
    assert not out["approved"] and len(out["vetoed"]) == 1


def test_describe_limits():
    pytest.importorskip("trade_risk")
    limits = describe_limits()
    assert any(l["name"] == "kill_switch" for l in limits)


# -- research lab ------------------------------------------------------------

def _need(pkg):
    pytest.importorskip(pkg)


def _bars(symbols=("SPY", "QQQ"), days=300):
    from trade_dashboard_web.engine import DataService
    ds = DataService()
    return {s: ds.get_bars(s, source="demo", days=days) for s in symbols}


def test_research_pairs_job():
    _need("trade_pairs")
    from trade_dashboard_web.engine import run_pairs_job
    r = run_pairs_job(["SPY", "QQQ", "IWM"], _bars(("SPY", "QQQ", "IWM")), lookback=100, max_pairs=3)
    assert r["source"] == "trade-pairs"
    assert len(r["pairs"]) <= 3
    assert all("hedge_ratio" in p and "cointegrated" in p for p in r["pairs"])


def test_research_orderbook_job():
    _need("trade_orderbook")
    from trade_dashboard_web.engine import run_orderbook_job
    r = run_orderbook_job(side="buy", quantity=100.0)
    assert r["source"] == "trade-orderbook"
    assert 0.0 <= r["fill_ratio"] <= 1.0


def test_research_optimize_job():
    _need("trade_optimize")
    from trade_dashboard_web.engine import run_optimize_job
    r = run_optimize_job(["SPY", "QQQ"], _bars(days=250), method="equal_weight")
    assert r["source"] == "trade-optimize"
    assert abs(sum(r["weights"].values()) - 1.0) < 1e-9
    assert len(r["frontier"]) == 20


def test_research_montecarlo_job():
    _need("trade_montecarlo")
    from trade_dashboard_web.engine import run_montecarlo_job
    r = run_montecarlo_job(["SPY", "QQQ"], _bars(days=250), n_paths=200, n_steps=60, seed=7)
    assert r["source"] == "trade-montecarlo"
    assert r["var"] >= 0


def test_research_vol_surface_job():
    _need("trade_volsurface")
    from trade_dashboard_web.engine import run_vol_surface_job
    r = run_vol_surface_job()
    assert r["source"] == "trade-volsurface"
    assert r["n_quotes"] > 0 and len(r["svi_fits"]) > 0


def test_research_factor_analysis_job():
    _need("trade_factors")
    from trade_dashboard_web.engine import run_factor_analysis_job
    r = run_factor_analysis_job(["SPY", "QQQ"], _bars(("SPY", "QQQ"), days=750), model="ff3", n_months=24)
    assert r["source"] == "trade-factors"
    assert set(r["assets"]) == {"SPY", "QQQ"}
    assert r["grs"]["pvalue"] is not None


def test_research_sentiment_price_job():
    _need("trade_sentiment_vs_price")
    from trade_dashboard_web.engine import run_sentiment_price_job
    r = run_sentiment_price_job("SPY", days=180)
    assert r["source"] == "trade-sentiment-vs-price"
    assert r["lead_lag"]["best_lag"] == 1  # planted lead recovered


def test_research_correlation_job():
    _need("trade_eda")
    from trade_dashboard_web.engine import run_correlation_job
    bars = _bars(("SPY", "QQQ", "IWM", "DIA"), days=300)
    r = run_correlation_job(["SPY", "QQQ", "IWM", "DIA"], bars,
                            method="pearson", lookback=200)
    assert r["source"] == "trade-eda"
    assert r["symbols"] == ["DIA", "IWM", "QQQ", "SPY"]
    assert r["n_obs"] == 199
    assert len(r["correlation"]["matrix"]) == 4
    assert r["diversification"]["effective_n_equal_weight"] <= 4
    assert set(r["describe"]) == {"DIA", "IWM", "QQQ", "SPY"}
    with pytest.raises(ValueError):
        run_correlation_job(["SPY"], bars)
    with pytest.raises(ValueError):
        run_correlation_job(["SPY", "QQQ"], bars, method="bogus")


# -- research lab: breadth / macro / stream / reconcile (v0.4.0) ------------------

def test_research_breadth_job():
    _need("trade_breadth")
    import json
    from trade_dashboard_web.engine import run_breadth_job
    r = run_breadth_job(seed=7, n_days=300, thrust_window=10)
    json.dumps(r)  # must survive a JSON round-trip
    assert r["source"] == "trade-breadth"
    assert r["n_symbols"] == 60
    assert r["n_days"] == 300
    snap = r["snapshot"]
    assert snap["regime"]
    assert 0.0 <= snap["fragility"] <= 1.0
    assert "indicators" in snap and "thrusts_recent" in snap
    with pytest.raises(ValueError):
        run_breadth_job(preset="bogus", n_days=300)
    with pytest.raises(ValueError):
        run_breadth_job(n_days=10)


def test_research_macro_job():
    _need("trade_macro")
    import json
    from trade_dashboard_web.engine import run_macro_job
    r = run_macro_job(seed=42, days=300)
    json.dumps(r)
    assert r["source"] == "trade-macro"
    assert r["days"] == 300
    snap = r["snapshot"]
    assert snap["regime"]
    assert snap["z_score"] is not None
    assert snap["ratio_vs_200dma"] is not None
    assert "transition_alert" in snap
    with pytest.raises(ValueError):
        run_macro_job(days=100)


def test_research_stream_demo_job():
    _need("trade_stream")
    import json
    from trade_dashboard_web.engine import run_stream_demo_job
    r = run_stream_demo_job(symbols=("AAA", "BBB"), seed=7, n_ticks=200)
    json.dumps(r)
    assert r["source"] == "trade-stream"
    assert r["demo"] is True
    assert r["n_ticks"] == 200
    assert set(r["symbols"]) == {"AAA", "BBB"}
    with pytest.raises(ValueError):
        run_stream_demo_job(symbols=())
    with pytest.raises(ValueError):
        run_stream_demo_job(n_ticks=0)
    with pytest.raises(ValueError):
        run_stream_demo_job(n_ticks=100_001)


def test_research_reconcile_demo_job():
    _need("trade_paper")
    import json
    from trade_dashboard_web.engine import run_reconcile_demo_job
    r = run_reconcile_demo_job()
    json.dumps(r)
    assert r["source"] == "trade-paper"
    assert r["demo"] is True
    assert r["paper_positions"] == {"AAPL": 10.0, "TSLA": 4.5, "NVDA": 2.0}
    assert r["broker_positions"] == {"AAPL": 10.0, "TSLA": 5.0}
    rc = r["reconcile"]
    assert rc["clean"] is False  # the demo ledger carries deliberate drift
    assert rc["matched"] == ["AAPL"]
    assert [m["symbol"] for m in rc["missing_from_broker"]] == ["NVDA"]
    assert [m["symbol"] for m in rc["quantity_mismatches"]] == ["TSLA"]


def _block(monkeypatch, package):
    """Make ``package`` unimportable (simulates a missing engine)."""
    import builtins
    real_import = builtins.__import__

    def fake(name, *args, **kwargs):
        if name == package:
            raise ImportError(f"No module named {name!r}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake)


@pytest.mark.parametrize(
    "job_fn,package,dist",
    [
        ("run_breadth_job", "trade_breadth", "trade-breadth"),
        ("run_macro_job", "trade_macro", "trade-macro"),
        ("run_stream_demo_job", "trade_stream", "trade-stream"),
        ("run_reconcile_demo_job", "trade_paper", "trade-paper"),
    ],
)
def test_missing_engine_raises_install_hint(monkeypatch, job_fn, package, dist):
    from trade_dashboard_web import engine
    _block(monkeypatch, package)
    with pytest.raises(RuntimeError) as exc_info:
        getattr(engine, job_fn)()
    assert "pip install" in str(exc_info.value)
    assert dist in str(exc_info.value)
