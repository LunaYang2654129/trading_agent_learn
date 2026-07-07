"""Financial Agent: financial statements and quantitative metrics."""

from __future__ import annotations

from multiple_agent_finance.agents.base import audit_event
from multiple_agent_finance.graph.state import StockAnalysisState
from multiple_agent_finance.tools.financial_tools import get_financial_metrics


def financial_agent_node(state: StockAnalysisState) -> dict:
    ticker = state["ticker"]
    metrics = get_financial_metrics(ticker)
    return {
        "financial_metrics": metrics,
        "shared_memory_refs": [{"agent": "financial_agent", "key": "financial_metrics"}],
        "audit_log": [audit_event("financial_agent", "financial metrics collected", metrics)],
    }
