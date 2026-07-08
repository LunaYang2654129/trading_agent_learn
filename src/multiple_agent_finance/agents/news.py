"""News Agent: external news, policy, research, and sentiment."""

from __future__ import annotations

from multiple_agent_finance.agents.base import audit_event
from multiple_agent_finance.graph.state import StockAnalysisState
from multiple_agent_finance.tools.news_tools import get_news_analysis


def news_agent_node(state: StockAnalysisState) -> dict:
    ticker = state["ticker"]
    sentiment = get_news_analysis(ticker, state.get("as_of_date"))
    return {
        "news_sentiment": sentiment,
        "external_data_refs": sentiment.get("sources", []),
        "shared_memory_refs": [{"agent": "news_agent", "key": "news_sentiment"}],
        "audit_log": [audit_event("news_agent", "news sentiment collected", sentiment)],
    }
