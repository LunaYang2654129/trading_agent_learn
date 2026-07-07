"""Risk Agent: market, financial, sentiment, operational, and systemic risks."""

from __future__ import annotations

from multiple_agent_finance.agents.base import audit_event
from multiple_agent_finance.graph.state import StockAnalysisState
from multiple_agent_finance.tools.risk_tools import get_risk_analysis


def risk_agent_node(state: StockAnalysisState) -> dict:
    ticker = state["ticker"]
    analysis = get_risk_analysis(ticker)
    return {
        "risk_analysis": analysis,
        "market_snapshot": analysis.get("market_snapshot", {}),
        "shared_memory_refs": [{"agent": "risk_agent", "key": "risk_analysis"}],
        "audit_log": [audit_event("risk_agent", "risk analysis collected", analysis)],
    }
