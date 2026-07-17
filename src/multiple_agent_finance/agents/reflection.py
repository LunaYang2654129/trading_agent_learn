"""Reflection Agent: review analysis output with the env-configured online LLM."""

from __future__ import annotations

import json
from typing import Any

from multiple_agent_finance.agents.base import audit_event
from multiple_agent_finance.agents.planner_connection import build_planner_retry_payload
from multiple_agent_finance.config.settings import settings
from multiple_agent_finance.graph.state import StockAnalysisState
from multiple_agent_finance.llm import get_agent_llm


REQUIRED_TECHNICAL_FIELDS = {
    "trend",
    "volume_signal",
    "macd_signal",
    "technical_risks",
    "support_resistance",
}
BLOCKING_STATE_FIELDS = {
    "company_profile",
    "data_ingestion_result",
    "financial_metrics",
    "market_data",
    "market_data.records",
    "news_sentiment",
    "technical_indicators",
}

REFLECTION_SYSTEM_PROMPT = """You are the Reflection Agent for a financial investment report.

Your responsibility is to review whether upstream multi-agent outputs are sufficient
to support the final conclusion. Do not regenerate the report.

Focus on:
1. Whether company, financial, news, technical, and market-data evidence is complete.
2. Whether the investment conclusion is supported by evidence.
3. Whether risk disclosure is sufficient.
4. Whether there are logical contradictions, omissions, hallucinations, or excessive certainty.
5. Whether the workflow should return to Planner for supplemental tasks.

Return JSON only. Do not output Markdown. JSON fields:
{
  "confidence": 0.0 to 1.0,
  "logic_score": 0.0 to 1.0,
  "risk_coverage_score": 0.0 to 1.0,
  "missing_items": ["missing or uncertain item"],
  "warnings": ["issue that needs attention"],
  "contradictions": ["logical contradiction"],
  "retry_tasks": ["actionable supplemental task for Planner"],
  "review_comment": "brief review conclusion"
}
"""


def _required_state_fields(chain_mode: str) -> tuple[str, ...]:
    if chain_mode == "technical":
        return ("technical_indicators",)
    return (
        "company_profile",
        "financial_metrics",
        "news_sentiment",
        "technical_indicators",
    )


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def _llm_runtime_metadata() -> dict[str, Any]:
    """Return non-secret Ark runtime metadata for diagnostics and audit."""

    return {
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "runtime_model": settings.llm_runtime_model,
        "endpoint_id_configured": bool(settings.llm_endpoint_id),
        "base_url": settings.llm_base_url,
        "api_key_configured": bool(settings.llm_api_key),
    }


def _sanitize_error(error: Exception) -> str:
    """Avoid leaking secrets if an SDK exception echoes request details."""

    message = str(error)
    if settings.llm_api_key:
        message = message.replace(settings.llm_api_key, "***")
    return message


def _ark_troubleshooting_hints(error_message: str) -> list[str]:
    """Generate actionable hints based on the Ark setup document."""

    hints = [
        "Run `python scripts/check_llm_connection.py` to verify offline configuration.",
        "Run `python scripts/check_llm_connection.py --live` to verify Ark connectivity.",
    ]
    if not settings.llm_api_key:
        hints.append("Set MAF_LLM_API_KEY in the project .env file.")
    if not settings.llm_endpoint_id:
        hints.append("Set MAF_LLM_ENDPOINT_ID to the Ark endpoint ID, such as ep-xxxxxxxx.")
    if "InvalidEndpointOrModel.NotFound" in error_message:
        hints.append(
            "Check whether MAF_LLM_ENDPOINT_ID is correct and enabled in Volcengine Ark."
        )
    return hints


def _dedupe_strings(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = str(value).strip()
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _has_market_evidence(state: StockAnalysisState) -> bool:
    """Accept preloaded market_data or Technical Agent yfinance market_snapshot."""

    if state.get("market_data", {}).get("records"):
        return True

    snapshot = state.get("technical_indicators", {}).get("market_snapshot", {})
    indicators = snapshot.get("technical_indicators", {})
    history_points = int(indicators.get("history_points", 0) or 0)
    return bool(snapshot.get("price") is not None and history_points > 0)


def _is_blocking_missing_item(item: Any, state: StockAnalysisState) -> bool:
    text = str(item).strip()
    if text in {"market_data", "market_data.records"} and _has_market_evidence(state):
        return False
    return text in BLOCKING_STATE_FIELDS


def _normalize_model_missing_items(
    raw_missing: list[Any],
    state: StockAnalysisState,
) -> tuple[list[str], list[str]]:
    blocking: list[str] = []
    suggestions: list[str] = []
    for item in raw_missing:
        text = str(item).strip()
        if not text:
            continue
        if _is_blocking_missing_item(text, state):
            blocking.append(text)
        else:
            suggestions.append(f"Model suggested supplemental note: {text}")
    return _dedupe_strings(blocking), _dedupe_strings(suggestions)


def _find_structural_gaps(state: StockAnalysisState) -> tuple[list[str], list[str]]:
    decision = state.get("decision_summary", {})
    missing = list(decision.get("missing_or_uncertain", []))
    warnings = list(decision.get("warnings", []))
    chain_mode = state.get("chain_mode", "full")
    technical = state.get("technical_indicators", {})

    for field in _required_state_fields(chain_mode):
        if not state.get(field):
            missing.append(field)

    if technical:
        missing_technical = sorted(
            field for field in REQUIRED_TECHNICAL_FIELDS if field not in technical
        )
        if missing_technical:
            missing.append("technical_indicators")
            warnings.append(f"Missing technical fields: {', '.join(missing_technical)}")
    else:
        missing.append("technical_indicators")

    if chain_mode == "technical":
        ingestion = state.get("data_ingestion_result", {})
        warnings.extend(str(item) for item in ingestion.get("warnings", []) if item)
        if not _has_market_evidence(state):
            missing.append("market_data.records")

    missing = [item for item in missing if _is_blocking_missing_item(item, state)]
    return sorted(set(missing)), _dedupe_strings(warnings)


def _build_report_snapshot(state: StockAnalysisState) -> dict[str, Any]:
    return {
        "ticker": state.get("ticker"),
        "user_request": state.get("user_request"),
        "as_of_date": state.get("as_of_date"),
        "chain_mode": state.get("chain_mode", "full"),
        "confidence_score": state.get("confidence_score"),
        "decision_summary": state.get("decision_summary", {}),
    }


def _build_evidence_snapshot(state: StockAnalysisState) -> dict[str, Any]:
    market_data = state.get("market_data", {})
    snapshot = state.get("technical_indicators", {}).get("market_snapshot", {})
    return {
        "planner_tasks": state.get("planner_tasks", {}),
        "company_profile": state.get("company_profile", {}),
        "financial_metrics": state.get("financial_metrics", {}),
        "news_sentiment": state.get("news_sentiment", {}),
        "technical_indicators": state.get("technical_indicators", {}),
        "backtest_result": state.get("backtest_result", {}),
        "market_data_summary": {
            "ticker": market_data.get("ticker"),
            "period": market_data.get("period"),
            "records": len(market_data.get("records", [])),
            "sources": market_data.get("sources", []),
            "warnings": market_data.get("warnings", []),
        },
        "technical_market_snapshot_summary": {
            "ticker": snapshot.get("ticker"),
            "latest_trading_date": snapshot.get("latest_trading_date"),
            "price_available": snapshot.get("price") is not None,
            "history_points": snapshot.get("technical_indicators", {}).get("history_points"),
            "sources": snapshot.get("sources", []),
        },
        "data_ingestion_result": state.get("data_ingestion_result", {}),
    }


def _extract_message_content(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, list):
        return "\n".join(str(item) for item in content)
    return str(content)


def _parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        stripped = stripped.removeprefix("json").strip()

    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        value = json.loads(stripped[start : end + 1])

    if not isinstance(value, dict):
        raise ValueError("Reflection model response is not a JSON object.")
    return value


def _call_online_reflection_model(state: StockAnalysisState) -> dict[str, Any]:
    llm = get_agent_llm("reflection")
    response = llm.invoke(
        [
            {"role": "system", "content": REFLECTION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Please review the current analysis result below.\n\n"
                    "[Report Snapshot Under Review]\n"
                    f"{_json_dump(_build_report_snapshot(state))}\n\n"
                    "[Upstream Evidence Snapshot]\n"
                    f"{_json_dump(_build_evidence_snapshot(state))}\n\n"
                    "Return JSON strictly according to the system instructions."
                ),
            },
        ]
    )
    return _parse_json_object(_extract_message_content(response))


def _fallback_review(state: StockAnalysisState, error: Exception) -> dict[str, Any]:
    missing, warnings = _find_structural_gaps(state)
    error_message = _sanitize_error(error)
    confidence = float(state.get("confidence_score", 0.0))
    confidence = max(0.0, confidence - min(len(missing) * 0.12, 0.5))
    retry_tasks = _build_retry_tasks(missing, confidence, state)
    return {
        "confidence": confidence,
        "logic_score": 0.6,
        "risk_coverage_score": 0.5,
        "missing_items": missing,
        "warnings": [
            *_dedupe_strings(warnings),
            f"Reflection online model failed: {error_message}",
            *_ark_troubleshooting_hints(error_message),
        ],
        "contradictions": [],
        "retry_tasks": retry_tasks,
        "review_comment": "Online Reflection failed; used structural fallback review.",
    }


def _build_retry_tasks(
    missing: list[str],
    confidence: float,
    state: StockAnalysisState,
) -> list[str]:
    chain_mode = state.get("chain_mode", "full")
    threshold = float(state.get("confidence_threshold", settings.default_confidence_threshold))
    retry_tasks: list[str] = []

    for item in missing:
        if item == "technical_indicators":
            retry_tasks.append(
                "Backfill technical_indicators: trend, volume_signal, macd_signal, "
                "technical_risks, support_resistance."
            )
        elif item in {"market_data", "market_data.records", "data_ingestion_result"}:
            retry_tasks.append(
                "Backfill market data: OHLCV records, volume, valuation helpers, sources."
            )
        else:
            retry_tasks.append(f"Backfill missing state field: {item}.")

    if confidence < threshold:
        if chain_mode == "technical":
            retry_tasks.append(
                "Improve technical-chain confidence with more complete OHLCV, volume, "
                "support/resistance, and valuation evidence."
            )
        else:
            retry_tasks.append(
                "Improve confidence with additional company, financial, news, "
                "and technical evidence."
            )
    return _dedupe_strings(retry_tasks)


def _coerce_review_result(raw: dict[str, Any], state: StockAnalysisState) -> dict[str, Any]:
    structural_missing, structural_warnings = _find_structural_gaps(state)
    confidence = float(raw.get("confidence", state.get("confidence_score", 0.0)) or 0.0)
    confidence = max(0.0, min(confidence, 1.0))

    model_missing, model_suggestions = _normalize_model_missing_items(
        list(raw.get("missing_items", [])),
        state,
    )
    missing = sorted(set([*structural_missing, *model_missing]))
    warnings = _dedupe_strings(
        [*structural_warnings, *(raw.get("warnings") or []), *model_suggestions]
    )
    generated_retry_tasks = _build_retry_tasks(missing, confidence, state)
    retry_tasks = _dedupe_strings(
        [*(raw.get("retry_tasks") or []), *generated_retry_tasks]
    )
    if _has_market_evidence(state):
        retry_tasks = [
            task for task in retry_tasks if not task.startswith("Backfill market data")
        ]

    return {
        "confidence": confidence,
        "decision_confidence": float(
            state.get("decision_summary", {}).get("confidence", 0.0) or 0.0
        ),
        "logic_score": float(raw.get("logic_score", 0.85) or 0.0),
        "risk_coverage_score": float(raw.get("risk_coverage_score", 0.8) or 0.0),
        "missing_items": missing,
        "warnings": warnings,
        "contradictions": list(raw.get("contradictions", [])),
        "retry_tasks": retry_tasks,
        "review_comment": raw.get("review_comment", "Reflection review completed."),
    }


def reflection_agent_node(state: StockAnalysisState) -> dict[str, Any]:
    """LangGraph node: review current state and decide whether to retry Planner."""

    retry_count = int(state.get("retry_count", 0))
    max_retries = int(state.get("max_retries", 1))
    threshold = float(state.get("confidence_threshold", settings.default_confidence_threshold))
    chain_mode = state.get("chain_mode", "full")

    try:
        raw_review = _call_online_reflection_model(state)
    except Exception as exc:
        raw_review = _fallback_review(state, exc)

    review = _coerce_review_result(raw_review, state)
    missing = review["missing_items"]
    confidence = review["confidence"]
    blocking_gaps = missing if retry_count < max_retries else []
    passed = not blocking_gaps and confidence >= threshold

    planner_retry_payload = None
    if not passed:
        planner_retry_payload = build_planner_retry_payload(
            state=state,
            retry_tasks=review["retry_tasks"],
            review_comment=review["review_comment"],
            confidence=confidence,
            threshold=threshold,
        )

    result = {
        "passed": passed,
        "chain_mode": chain_mode,
        "completeness_score": round(max(0.25, 1.0 - 0.16 * len(missing)), 2),
        "logic_score": round(max(0.0, min(review["logic_score"], 1.0)), 2),
        "risk_coverage_score": round(max(0.0, min(review["risk_coverage_score"], 1.0)), 2),
        "decision_confidence": review["decision_confidence"],
        "reflection_confidence": confidence,
        "missing_items": missing,
        "warnings": review["warnings"],
        "contradictions": review["contradictions"],
        "retry_tasks": [] if passed else review["retry_tasks"],
        "review_comment": review["review_comment"],
        "model_config": _llm_runtime_metadata(),
        "planner_retry_payload": planner_retry_payload,
    }

    updates: dict[str, Any] = {
        "confidence_score": confidence,
        "reflection_result": result,
        "audit_log": [audit_event("reflection_agent", "reflection completed", result)],
    }
    if not passed and retry_count < max_retries:
        updates["retry_count"] = retry_count + 1
    return updates
