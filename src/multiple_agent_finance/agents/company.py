"""Company Agent: evidence-grounded qualitative fundamental analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from multiple_agent_finance.agents.base import audit_event
from multiple_agent_finance.agents.company_schema import CompanyAnalysis
from multiple_agent_finance.graph.state import StockAnalysisState
from multiple_agent_finance.llm import get_agent_llm
from multiple_agent_finance.tools.company_tools import get_company_profile


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "company.md"


def _load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _build_messages(state: StockAnalysisState, evidence: dict[str, Any]) -> list[Any]:
    context = {
        "ticker": str(state.get("ticker", evidence.get("ticker", "UNKNOWN"))).upper(),
        "as_of_date": state.get("as_of_date"),
        "user_request": state.get("user_request", ""),
        "planner_task": state.get("planner_tasks", {}).get("company", ""),
        "company_data": evidence,
        "knowledge_base_refs": state.get("knowledge_base_refs", []),
        "shared_memory_refs": state.get("shared_memory_refs", []),
    }
    return [
        SystemMessage(content=_load_prompt()),
        HumanMessage(
            content=(
                "Analyze the following company evidence and return only the required JSON.\n"
                + json.dumps(context, ensure_ascii=False, indent=2, default=str)
            )
        ),
    ]


def _extract_message_content(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("text"):
                parts.append(str(item["text"]))
        return "\n".join(parts)
    return str(content or "")


def _parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        first_newline = stripped.find("\n")
        if first_newline >= 0:
            stripped = stripped[first_newline + 1 :]
        if stripped.endswith("```"):
            stripped = stripped[:-3]
        stripped = stripped.strip()

    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("LLM response did not contain a JSON object")
        value = json.loads(stripped[start : end + 1])

    if not isinstance(value, dict):
        raise ValueError("LLM response must be a JSON object")
    return value


def _validated_result(
    value: Any,
    *,
    ticker: str,
    as_of_date: str | None,
) -> dict[str, Any]:
    result = CompanyAnalysis.model_validate(value)
    result = result.model_copy(update={"ticker": ticker, "as_of_date": as_of_date})
    return result.model_dump(mode="json")


def _evidence_lines(section: dict[str, Any]) -> list[str]:
    return [f"{key}: {value}" for key, value in section.items() if value is not None]


def _build_degraded_analysis(
    evidence: dict[str, Any],
    *,
    ticker: str,
    as_of_date: str | None,
    errors: list[Exception],
) -> dict[str, Any]:
    source_warnings = [str(item) for item in evidence.get("warnings", []) if item]
    model_warnings = [f"Company LLM analysis failed: {error}" for error in errors]
    warnings = [*source_warnings, *model_warnings]
    if not warnings:
        warnings = ["Company analysis evidence is incomplete."]

    business_summary = str(
        evidence.get("business_summary") or "insufficient_evidence"
    )
    sector = str(evidence.get("sector") or "unknown")
    industry = str(evidence.get("industry") or "unknown")
    company_name = str(evidence.get("company_name") or ticker)
    main_products = [str(item) for item in evidence.get("main_products", []) if item]
    financial_evidence = dict(evidence.get("financial_evidence") or {})
    growth_evidence = dict(evidence.get("growth_evidence") or {})
    risk_message = "Company analysis is degraded because model output is unavailable."

    result = CompanyAnalysis(
        ticker=ticker,
        as_of_date=as_of_date,
        company_name=company_name,
        status="degraded",
        business_model={
            "summary": business_summary,
            "products_services": main_products,
            "revenue_drivers": [],
            "evidence": [business_summary] if business_summary != "insufficient_evidence" else [],
        },
        industry_position={
            "sector": sector,
            "industry": industry,
            "position": "insufficient_evidence",
            "market_position_evidence": _evidence_lines(
                dict(evidence.get("competitive_evidence") or {})
            ),
        },
        competitive_advantages=[],
        financial_health={
            "assessment": "insufficient_evidence",
            "strengths": [],
            "concerns": [],
            "evidence": _evidence_lines(financial_evidence),
        },
        growth={
            "assessment": "insufficient_evidence",
            "growth_drivers": [],
            "constraints": [],
            "evidence": _evidence_lines(growth_evidence),
        },
        risk_factors=[
            {"risk": risk_message, "severity": "unknown", "evidence": warnings[0]}
        ],
        confidence=0.2 if evidence else 0.05,
        warnings=warnings,
        sources=list(evidence.get("sources", [])),
        business_summary=business_summary,
        sector=sector,
        industry=industry,
        main_products=main_products,
        competitive_position="insufficient_evidence",
        key_risks=[risk_message],
    )
    return result.model_dump(mode="json")


def _invoke_company_model(
    messages: list[Any],
    evidence: dict[str, Any],
    *,
    ticker: str,
    as_of_date: str | None,
) -> dict[str, Any]:
    errors: list[Exception] = []
    try:
        llm = get_agent_llm("company")
    except Exception as exc:
        return _build_degraded_analysis(
            evidence,
            ticker=ticker,
            as_of_date=as_of_date,
            errors=[exc],
        )

    try:
        structured_llm = llm.with_structured_output(CompanyAnalysis)
        raw = structured_llm.invoke(messages)
        if raw is None:
            raise ValueError("structured output returned no parsed result")
        return _validated_result(raw, ticker=ticker, as_of_date=as_of_date)
    except Exception as exc:
        errors.append(exc)

    try:
        response = llm.invoke(messages)
        raw_json = _parse_json_object(_extract_message_content(response))
        return _validated_result(raw_json, ticker=ticker, as_of_date=as_of_date)
    except Exception as exc:
        errors.append(exc)
        return _build_degraded_analysis(
            evidence,
            ticker=ticker,
            as_of_date=as_of_date,
            errors=errors,
        )


def company_agent_node(state: StockAnalysisState) -> dict[str, Any]:
    """Analyze company fundamentals and return a stable JSON state update."""

    ticker = state["ticker"].upper()
    as_of_date = state.get("as_of_date")
    evidence = state.get("company_data") or get_company_profile(
        ticker,
        as_of_date=as_of_date,
    )
    messages = _build_messages(state, evidence)
    profile = _invoke_company_model(
        messages,
        evidence,
        ticker=ticker,
        as_of_date=as_of_date,
    )
    message = (
        "company analysis completed"
        if profile["status"] == "success"
        else "company analysis completed with degraded output"
    )
    return {
        "company_profile": profile,
        "shared_memory_refs": [{"agent": "company_agent", "key": "company_profile"}],
        "audit_log": [audit_event("company_agent", message, profile)],
    }
