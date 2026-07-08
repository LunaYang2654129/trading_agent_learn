"""Planner Agent: decomposes user intent into specialist tasks."""

from __future__ import annotations

from multiple_agent_finance.agents.base import audit_event
from multiple_agent_finance.graph.state import StockAnalysisState


DEFAULT_REQUEST = "Analyze company fundamentals, financials, news sentiment, and technical signals."


def planner_agent_node(state: StockAnalysisState) -> dict:
    ticker = state["ticker"].upper()
    request = state.get("user_request", DEFAULT_REQUEST)
    retry_count = int(state.get("retry_count", 0))
    retry_tasks = state.get("reflection_result", {}).get("retry_tasks", [])
    chain_mode = state.get("chain_mode", "full")

    tasks = {
        "user_focus": request,
        "retry_tasks": retry_tasks,
    }

    if chain_mode == "technical":
        tasks.update(
            {
                "data": (
                    f"Confirm that OHLCV bars, volume, PE/PB, sources, and ingestion status "
                    f"are available for {ticker}."
                ),
                "technical": (
                    f"Analyze {ticker} using OHLCV bars, volume, MA20/MA60/MA200, MACD, RSI, "
                    "Bollinger Bands, ATR, PE/PB, and support/resistance."
                ),
                "decision": (
                    "Generate a technical-chain risk judgment from structured technical indicators. "
                    "Do not output real trading orders."
                ),
                "reflection": (
                    "Validate technical indicator completeness, source coverage, and actionable retry tasks."
                ),
            }
        )
        message = "planned technical single-link tasks"
    else:
        tasks.update(
            {
                "company": (
                    f"Analyze {ticker}'s core business, industry position, competitive landscape, "
                    "and company quality."
                ),
                "financial": (
                    f"Analyze {ticker}'s revenue, profit, ROE, leverage, and operating cash-flow quality."
                ),
                "news": f"Collect and classify recent news, policy, research, and sentiment signals for {ticker}.",
                "technical": (
                    f"Analyze {ticker}'s OHLCV bars, volume, MACD, RSI, Bollinger Bands, ATR, "
                    "and valuation helper indicators."
                ),
            }
        )
        message = "planned parallel specialist tasks"

    return {
        "ticker": ticker,
        "planner_tasks": tasks,
        "retry_count": retry_count,
        "audit_log": [audit_event("planner", message, tasks)],
    }
