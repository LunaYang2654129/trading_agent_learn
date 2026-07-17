"""Backtest Agent: six-month forward-return event study."""

from __future__ import annotations

from multiple_agent_finance.agents.base import audit_event
from multiple_agent_finance.graph.state import StockAnalysisState
from multiple_agent_finance.tools.backtest_tools import get_six_month_forward_return_backtest


def backtest_agent_node(state: StockAnalysisState) -> dict:
    ticker = state["ticker"].upper()
    kwargs = {}
    if state.get("backtest_lookback_days") is not None:
        kwargs["lookback_days"] = int(state["backtest_lookback_days"])
    if state.get("backtest_horizons"):
        kwargs["horizons"] = tuple(int(horizon) for horizon in state["backtest_horizons"])

    result = get_six_month_forward_return_backtest(
        ticker,
        as_of_date=state.get("as_of_date"),
        market_data=state.get("market_data"),
        **kwargs,
    )
    horizons = "/".join(str(horizon) for horizon in result.get("horizons", []))
    return {
        "backtest_result": result,
        "shared_memory_refs": [{"agent": "backtest_agent", "key": "backtest_result"}],
        "audit_log": [
            audit_event(
                "backtest_agent",
                f"forward returns calculated for {horizons or 'default'} horizons",
                result,
            )
        ],
    }
