"""Structured JSON contract for Company Agent analysis."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class BusinessModelAnalysis(BaseModel):
    summary: str
    products_services: list[str] = Field(default_factory=list)
    revenue_drivers: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class IndustryPositionAnalysis(BaseModel):
    sector: str
    industry: str
    position: str
    market_position_evidence: list[str] = Field(default_factory=list)


class CompetitiveAdvantage(BaseModel):
    advantage: str
    durability: Literal["low", "medium", "high", "unknown"]
    evidence: str


class FinancialHealthAnalysis(BaseModel):
    assessment: str
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class GrowthAnalysis(BaseModel):
    assessment: str
    growth_drivers: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class RiskFactor(BaseModel):
    risk: str
    severity: Literal["low", "medium", "high", "unknown"]
    evidence: str


class CompanyAnalysis(BaseModel):
    ticker: str
    as_of_date: str | None = None
    company_name: str
    status: Literal["success", "degraded"]
    business_model: BusinessModelAnalysis
    industry_position: IndustryPositionAnalysis
    competitive_advantages: list[CompetitiveAdvantage] = Field(default_factory=list)
    financial_health: FinancialHealthAnalysis
    growth: GrowthAnalysis
    risk_factors: list[RiskFactor] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)

    # Compatibility fields read by the current Decision and storage layers.
    business_summary: str
    sector: str
    industry: str
    main_products: list[str] = Field(default_factory=list)
    competitive_position: str
    key_risks: list[str] = Field(default_factory=list)
