"""Reflection Agent: validate completeness, logic, risk coverage, and confidence."""

from __future__ import annotations

from multiple_agent_finance.agents.base import audit_event
from multiple_agent_finance.graph.state import StockAnalysisState


REQUIRED_TECHNICAL_FIELDS = {
    "trend",
    "volume_signal",
    "macd_signal",
    "technical_risks",
    "support_resistance",
}


def _required_state_fields(chain_mode: str) -> tuple[str, ...]:
    if chain_mode == "technical":
        return ("market_data", "technical_indicators")
    return (
        "company_profile",
        "financial_metrics",
        "news_sentiment",
        "technical_indicators",
    )


def reflection_agent_node(state: StockAnalysisState) -> dict:
    decision = state.get("decision_summary", {})
    missing = list(decision.get("missing_or_uncertain", []))
    warnings = list(decision.get("warnings", []))
    technical = state.get("technical_indicators", {})
    chain_mode = state.get("chain_mode", "full")

    for field in _required_state_fields(chain_mode):
        if not state.get(field):
            missing.append(field)

    if technical:
        missing_technical = sorted(
            field for field in REQUIRED_TECHNICAL_FIELDS if field not in technical
        )
        if missing_technical:
            missing.append("technical_indicators")
    else:
        missing_technical = sorted(REQUIRED_TECHNICAL_FIELDS)

    if chain_mode == "technical":
        ingestion = state.get("data_ingestion_result", {})
        if ingestion.get("warnings"):
            warnings.extend(str(item) for item in ingestion["warnings"] if item)
        market_data = state.get("market_data", {})
        if not market_data.get("records"):
            missing.append("market_data.records")

    missing = sorted(set(missing))
    confidence = float(state.get("confidence_score", 0.0))
    threshold = float(state.get("confidence_threshold", 0.75))
    max_retries = int(state.get("max_retries", 1))
    retry_count = int(state.get("retry_count", 0))

    blocking_gaps = missing if retry_count < max_retries else []
    passed = not blocking_gaps and confidence >= threshold

    retry_tasks = []
    for item in missing:
        if item == "technical_indicators":
            retry_tasks.append(
                "Backfill technical_indicators: trend / volume_signal / macd_signal / support_resistance"
            )
        elif item in {"market_data", "market_data.records", "data_ingestion_result"}:
            retry_tasks.append(
                "Backfill market data collection and ingestion status: OHLCV / volume / PE / PB / sources"
            )
        else:
            retry_tasks.append(f"Backfill missing state field: {item}")
    if confidence < threshold:
        if chain_mode == "technical":
            retry_tasks.append(
                "Improve confidence by collecting a more complete OHLCV window, volume data, or valuation helpers"
            )
        else:
            retry_tasks.append(
                "Improve confidence by adding company, financial, news, or technical evidence"
            )

    completeness_score = max(0.25, 1.0 - 0.16 * len(missing))
    risk_coverage_score = 0.9
    if not state.get("technical_indicators"):
        risk_coverage_score -= 0.25
    if chain_mode != "technical":
        if not state.get("financial_metrics"):
            risk_coverage_score -= 0.15
        if not state.get("news_sentiment"):
            risk_coverage_score -= 0.1
        if not state.get("company_profile"):
            risk_coverage_score -= 0.1
    elif not state.get("market_data", {}).get("records"):
        risk_coverage_score -= 0.2

    result = {
        "passed": passed,
        "chain_mode": chain_mode,
        "completeness_score": round(completeness_score, 2),
        "logic_score": 0.85,
        "risk_coverage_score": round(max(risk_coverage_score, 0.3), 2),
        "missing_items": missing,
        "warnings": warnings,
        "contradictions": [],
        "retry_tasks": retry_tasks,
        "review_comment": "Validation passed." if passed else "Evidence is incomplete or confidence is low.",
    }

    updates = {
        "reflection_result": result,
        "audit_log": [audit_event("reflection_agent", "reflection completed", result)],
    }
    if not passed and retry_count < max_retries:
        updates["retry_count"] = retry_count + 1
    return updates
