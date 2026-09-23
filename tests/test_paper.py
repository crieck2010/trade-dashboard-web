"""Tests for the Paper tab backend (engine/paper_service.py)."""

from __future__ import annotations

import json

import pytest

from trade_dashboard_web.engine import (
    paper_approvals,
    paper_approve,
    paper_available,
    paper_fidelity,
    paper_status,
)


@pytest.fixture
def cfg_path(tmp_path):
    p = tmp_path / "paper-config.json"
    p.write_text(json.dumps({
        "broker": {"name": "fake"},
        "data_source": "demo",
        "db_path": str(tmp_path / "trade-paper.db"),
        "symbols_equities": ["AAA"],
        "symbols_crypto": [],
    }))
    return str(p)


def test_paper_available_flag():
    ok, _ = paper_available()
    assert ok  # trade-paper is installed in the test env


def test_paper_status_fake_broker(cfg_path):
    s = paper_status(cfg_path)
    assert s["available"] and s["paper_only"]
    assert s["equity"] == 100000.0
    assert s["positions"] == []
    assert s["pending_approvals"] == 0


def test_paper_approve_roundtrip(cfg_path):
    import trade_paper
    from trade_paper.config import PaperConfig
    from trade_paper.ledger import Ledger
    from trade_paper.models import Discovery

    cfg = PaperConfig.load(cfg_path)
    ledger = Ledger(cfg.db_path)
    d = Discovery(strategy="s", symbols=("AAA",), direction="long",
                  metrics={"sharpe_ratio": 1.5})
    ledger.record_discovery(d)
    aid = ledger.submit_approval(d, {"chain": "test"})
    ledger.close()

    out = paper_approve(cfg_path, aid, reason="test")
    assert out["approved"] == aid

    approvals = paper_approvals(cfg_path, status="approved")
    assert len(approvals["approvals"]) == 1
    assert approvals["approvals"][0]["decided_by"] == "user"


def test_paper_fidelity_empty(cfg_path):
    f = paper_fidelity(cfg_path)
    assert f["available"] and f["strategies"] == {}
