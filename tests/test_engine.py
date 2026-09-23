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
