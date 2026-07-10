"""Interfaces that connect Reflection feedback back to Planner."""

from __future__ import annotations

from typing import Any

from multiple_agent_finance.graph.state import StockAnalysisState


def build_retry_instruction(
    *,
    ticker: str,
    retry_tasks: list[str],
    review_comment: str,
    confidence: float,
    threshold: float,
) -> str:
    """Create a Planner-readable retry instruction from Reflection feedback."""

    tasks = "\n".join(f"- {task}" for task in retry_tasks) or "- No explicit retry task."
    return (
        f"Reflection review did not pass for {ticker}.\n"
        f"Confidence: {confidence:.2f}; threshold: {threshold:.2f}.\n\n"
        f"Review comment:\n{review_comment}\n\n"
        f"Please re-plan the following tasks:\n{tasks}"
    )


def build_planner_retry_payload(
    *,
    state: StockAnalysisState,
    retry_tasks: list[str],
    review_comment: str,
    confidence: float,
    threshold: float,
) -> dict[str, Any]:
    """Return the payload that product/UI code can send to Planner retry."""

    ticker = str(state.get("ticker", "UNKNOWN")).upper()
    instruction = build_retry_instruction(
        ticker=ticker,
        retry_tasks=retry_tasks,
        review_comment=review_comment,
        confidence=confidence,
        threshold=threshold,
    )
    return {
        "target_agent": "planner_agent",
        "target_interface": "retry",
        "ticker": ticker,
        "chain_mode": state.get("chain_mode", "full"),
        "retry_count": int(state.get("retry_count", 0)),
        "retry_tasks": retry_tasks,
        "messages": [{"role": "user", "content": instruction}],
        "reflection_review": {
            "confidence": confidence,
            "threshold": threshold,
            "review_comment": review_comment,
        },
    }


def extract_retry_tasks(payload: dict[str, Any]) -> list[str]:
    """Read retry tasks from a Planner retry payload."""

    return [str(task) for task in payload.get("retry_tasks", []) if task]


def build_planner_state_patch(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert a retry payload into fields that Planner can consume in state."""

    return {
        "reflection_result": {
            "retry_tasks": extract_retry_tasks(payload),
            "review_comment": payload.get("reflection_review", {}).get("review_comment", ""),
        }
    }
