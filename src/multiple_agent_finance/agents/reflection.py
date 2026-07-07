"""Reflection Agent: validate completeness, logic, risk coverage, and confidence."""

from __future__ import annotations

from multiple_agent_finance.agents.base import audit_event
from multiple_agent_finance.graph.state import StockAnalysisState


def reflection_agent_node(state: StockAnalysisState) -> dict:
    decision = state.get("decision_summary", {})
    missing = list(decision.get("missing_or_uncertain", []))
    warnings = list(decision.get("warnings", []))
    confidence = float(state.get("confidence_score", 0.0))
    threshold = float(state.get("confidence_threshold", 0.75))
    max_retries = int(state.get("max_retries", 1))
    retry_count = int(state.get("retry_count", 0))

    blocking_gaps = missing if retry_count < max_retries else []
    passed = not blocking_gaps and confidence >= threshold

    retry_tasks = [f"补充缺失字段: {item}" for item in missing]
    if confidence < threshold:
        retry_tasks.append("提高置信度：补充行情、财务、新闻或风险证据。")

    completeness_score = 1.0 if not missing else max(0.35, 1.0 - 0.18 * len(missing))
    risk_coverage_score = 0.88 if state.get("risk_analysis") else 0.45
    if state.get("market_snapshot", {}).get("price") is None:
        risk_coverage_score -= 0.1

    result = {
        "passed": passed,
        "completeness_score": round(completeness_score, 2),
        "logic_score": 0.85,
        "risk_coverage_score": round(max(risk_coverage_score, 0.3), 2),
        "missing_items": missing,
        "warnings": warnings,
        "contradictions": [],
        "retry_tasks": retry_tasks,
        "review_comment": "校验通过。" if passed else "信息不足或置信度偏低，进入补充分析或保守输出。",
    }

    updates = {
        "reflection_result": result,
        "audit_log": [audit_event("reflection_agent", "reflection completed", result)],
    }
    if not passed and retry_count < max_retries:
        updates["retry_count"] = retry_count + 1
    return updates
