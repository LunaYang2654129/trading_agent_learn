"""Company Agent: company profile and qualitative fundamentals."""

from __future__ import annotations

from multiple_agent_finance.agents.base import audit_event
from multiple_agent_finance.graph.state import StockAnalysisState
from multiple_agent_finance.tools.company_tools import get_company_profile


def company_agent_node(state: StockAnalysisState) -> dict:
    ticker = state["ticker"]
    profile = get_company_profile(ticker)
    return {
        "company_profile": profile,
        "shared_memory_refs": [{"agent": "company_agent", "key": "company_profile"}],
        "audit_log": [audit_event("company_agent", "company profile collected", profile)],
    }
