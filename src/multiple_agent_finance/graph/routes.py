"""Conditional routing for the LangGraph workflow."""

from __future__ import annotations

from multiple_agent_finance.graph.state import StockAnalysisState


def confidence_route(state: StockAnalysisState) -> str:
    """Route to retry or final report based on Reflection confidence."""
    reflection = state.get("reflection_result", {})
    passed = bool(reflection.get("passed", False))
    confidence = float(state.get("confidence_score", 0.0))
    threshold = float(state.get("confidence_threshold", 0.75))
    retry_count = int(state.get("retry_count", 0))
    max_retries = int(state.get("max_retries", 1))

    if passed and confidence >= threshold:
        return "final_report"
    if retry_count < max_retries:
        return "planner"
    return "final_report"
