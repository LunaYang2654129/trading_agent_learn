"""Technical Agent: price action, volume, valuation, and indicators."""

from __future__ import annotations

from multiple_agent_finance.agents.base import audit_event
from multiple_agent_finance.graph.state import StockAnalysisState
from multiple_agent_finance.tools.technical_tools import (
    get_technical_indicators,
    get_technical_indicators_from_market_data,
)


def technical_agent_node(state: StockAnalysisState) -> dict:
    ticker = state["ticker"].upper()
    market_data = state.get("market_data", {})
    if market_data.get("records"):
        indicators = get_technical_indicators_from_market_data(
            ticker,
            market_data,
            as_of_date=state.get("as_of_date"),
        )
        message = "technical indicators calculated from collected market data"
    else:
        indicators = get_technical_indicators(
            ticker,
            state.get("as_of_date"),
            period=state.get("market_period", "1y"),
        )
        message = "technical indicators collected"
    return {
        "technical_indicators": indicators,
        "shared_memory_refs": [{"agent": "technical_agent", "key": "technical_indicators"}],
        "audit_log": [
            audit_event("technical_agent", message, indicators)
        ],
    }
