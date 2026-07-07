"""Global State shared by all LangGraph nodes."""

from __future__ import annotations

from operator import add
from typing import Annotated, Any, Literal, TypedDict


class StockAnalysisState(TypedDict, total=False):
    # User input and workflow control.
    ticker: str
    user_request: str
    as_of_date: str
    retry_count: int
    max_retries: int
    confidence_threshold: float

    # Planner and parallel agent outputs.
    planner_tasks: dict[str, Any]
    company_profile: dict[str, Any]
    financial_metrics: dict[str, Any]
    news_analysis: dict[str, Any]
    risk_analysis: dict[str, Any]
    market_snapshot: dict[str, Any]

    # Shared memory / knowledge base references.
    shared_memory_refs: Annotated[list[dict[str, Any]], add]
    knowledge_base_refs: Annotated[list[dict[str, Any]], add]
    external_data_refs: Annotated[list[dict[str, Any]], add]

    # Decision and reflection.
    decision_summary: dict[str, Any]
    reflection_result: dict[str, Any]
    confidence_score: float
    route: Literal["retry", "final"]

    # Final output and audit.
    final_report: str
    final_report_path: str
    audit_log: Annotated[list[dict[str, Any]], add]
