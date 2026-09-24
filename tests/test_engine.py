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
