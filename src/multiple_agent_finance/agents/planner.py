"""Planner Agent: decomposes user intent into parallel analysis tasks."""

from __future__ import annotations

from multiple_agent_finance.agents.base import audit_event
from multiple_agent_finance.graph.state import StockAnalysisState


def planner_agent_node(state: StockAnalysisState) -> dict:
    ticker = state["ticker"].upper()
    request = state.get("user_request", "综合分析股票基本面、市场表现、新闻情绪和风险。")
    retry_count = int(state.get("retry_count", 0))
    reflection = state.get("reflection_result", {})
    retry_tasks = reflection.get("retry_tasks", [])

    tasks = {
        "company": f"分析 {ticker} 的主营业务、行业地位、竞争格局和公司质量。",
        "financial": f"分析 {ticker} 的营收、利润、ROE、负债率和现金流质量。",
        "news": f"检索 {ticker} 的新闻、政策、研报和舆情变化。",
        "risk": f"识别 {ticker} 的市场、财务、舆情、经营和系统性风险。",
        "user_focus": request,
        "retry_tasks": retry_tasks,
    }

    return {
        "ticker": ticker,
        "planner_tasks": tasks,
        "retry_count": retry_count,
        "audit_log": [audit_event("planner", "planned parallel tasks", tasks)],
    }
