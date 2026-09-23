"""Pure-logic services backing the dashboard.  No web-framework imports."""

from .backtest_service import run_backtest_job
from .data_service import DataService, bar_to_dict
from .desk_service import run_desk_job
from .risk_service import describe_limits, evaluate_orders_job
from .strategy_service import describe_strategy, list_strategies

__all__ = [
    "DataService",
    "bar_to_dict",
    "describe_limits",
    "describe_strategy",
    "evaluate_orders_job",
    "list_strategies",
    "run_backtest_job",
    "run_desk_job",
]
