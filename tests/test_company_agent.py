from __future__ import annotations

import json
from copy import deepcopy

import pytest
from pydantic import ValidationError

from multiple_agent_finance.agents.company_schema import CompanyAnalysis


def _valid_company_payload() -> dict:
    return {
        "ticker": "AAPL",
        "as_of_date": "2026-07-15",
        "company_name": "Apple Inc.",
        "status": "success",
        "business_model": {
            "summary": "Consumer hardware and services ecosystem.",
            "products_services": ["iPhone", "Services"],
            "revenue_drivers": ["Installed base", "Services attach rate"],
            "evidence": ["Company profile describes devices and services."],
        },
        "industry_position": {
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "position": "Global category leader.",
            "market_position_evidence": ["Premium-device brand and ecosystem."],
        },
        "competitive_advantages": [
            {
                "advantage": "Integrated ecosystem",
                "durability": "high",
                "evidence": "Hardware, software, and services are integrated.",
            }
        ],
        "financial_health": {
            "assessment": "healthy",
            "strengths": ["Positive free cash flow"],
            "concerns": ["Debt requires monitoring"],
            "evidence": ["Free cash flow is positive in the supplied evidence."],
        },
        "growth": {
            "assessment": "moderate",
            "growth_drivers": ["Services"],
            "constraints": ["Mature handset market"],
            "evidence": ["Revenue growth is positive in the supplied evidence."],
        },
        "risk_factors": [
            {
                "risk": "Supply-chain concentration",
                "severity": "medium",
                "evidence": "The supplied profile identifies concentrated manufacturing.",
            }
        ],
        "confidence": 0.82,
        "warnings": [],
        "sources": [{"type": "company_profile", "name": "fixture"}],
        "business_summary": "Consumer hardware and services ecosystem.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "main_products": ["iPhone", "Services"],
        "competitive_position": "Global category leader.",
        "key_risks": ["Supply-chain concentration"],
    }


def _set_nested(payload: dict, path: tuple, value: object) -> None:
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value


def test_company_analysis_schema_serializes_six_dimensions():
    analysis = CompanyAnalysis.model_validate(_valid_company_payload())

    payload = analysis.model_dump(mode="json")

    assert payload["business_model"]["summary"] == (
        "Consumer hardware and services ecosystem."
    )
    assert payload["industry_position"]["position"] == "Global category leader."
    assert payload["competitive_advantages"][0]["durability"] == "high"
    assert payload["financial_health"]["assessment"] == "healthy"
    assert payload["growth"]["assessment"] == "moderate"
    assert payload["risk_factors"][0]["severity"] == "medium"
    assert payload["competitive_position"]
    assert payload["key_risks"]
    json.dumps(payload)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("confidence",), 1.5),
        (("competitive_advantages", 0, "durability"), "permanent"),
        (("risk_factors", 0, "severity"), "critical"),
    ],
)
def test_company_analysis_schema_rejects_invalid_control_values(path, value):
    payload = deepcopy(_valid_company_payload())
    _set_nested(payload, path, value)

    with pytest.raises(ValidationError):
        CompanyAnalysis.model_validate(payload)
