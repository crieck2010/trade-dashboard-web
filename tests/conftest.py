"""Shared fixtures."""

from __future__ import annotations

import pytest

from trade_dashboard_web.engine import DataService


@pytest.fixture
def data_service():
    return DataService()


@pytest.fixture
def demo_bars():
    return DataService().get_bars("SPY", source="demo", days=200)
