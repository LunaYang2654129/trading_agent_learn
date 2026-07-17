"""MySQL persistence for LangGraph analysis state."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from multiple_agent_finance.config.settings import settings
from multiple_agent_finance.graph.state import StockAnalysisState


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


class DatabaseStore:
    """Persist one completed analysis run into MySQL."""

    def __init__(self, mysql_url: str | None = None, engine: Engine | None = None) -> None:
        self.engine = engine or create_engine(mysql_url or settings.mysql_url, pool_pre_ping=True)

    def save_market_data(self, market_data: dict[str, Any]) -> int:
        """Persist normalized OHLCV market bars collected before the agent chain."""

        ticker = str(market_data.get("ticker", "")).upper()
        records = market_data.get("records", [])
        if not ticker or not records:
            return 0

        source = "yfinance"
        sources = market_data.get("sources", [])
        if sources and isinstance(sources[0], dict):
            source = str(sources[0].get("name") or source)

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO symbols (ticker)
                    VALUES (:ticker)
                    ON DUPLICATE KEY UPDATE ticker = VALUES(ticker)
                    """
                ),
                {"ticker": ticker},
            )
            for record in records:
                conn.execute(
                    text(
                        """
                        INSERT INTO market_bars (
                          ticker, bar_date, open_price, high_price, low_price,
                          close_price, volume, source
                        )
                        VALUES (
                          :ticker, :bar_date, :open_price, :high_price, :low_price,
                          :close_price, :volume, :source
                        )
                        ON DUPLICATE KEY UPDATE
                          open_price = VALUES(open_price),
                          high_price = VALUES(high_price),
                          low_price = VALUES(low_price),
                          close_price = VALUES(close_price),
                          volume = VALUES(volume),
                          updated_at = CURRENT_TIMESTAMP
                        """
                    ),
                    {
                        "ticker": ticker,
                        "bar_date": record.get("date"),
                        "open_price": _decimal(record.get("open")),
                        "high_price": _decimal(record.get("high")),
                        "low_price": _decimal(record.get("low")),
                        "close_price": _decimal(record.get("close")),
                        "volume": _int(record.get("volume")),
                        "source": source,
                    },
                )
        return len(records)

    def save_analysis_state(self, state: StockAnalysisState) -> str:
        run_id = str(uuid4())
        ticker = str(state.get("ticker", "")).upper()
        company = state.get("company_profile", {})
        financial = state.get("financial_metrics", {})
        news = state.get("news_sentiment", {})
        technical = state.get("technical_indicators", {})
        market = technical.get("market_snapshot", {})
        decision = state.get("decision_summary", {})
        reflection = state.get("reflection_result", {})

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO symbols (ticker, company_name, sector, industry, website)
                    VALUES (:ticker, :company_name, :sector, :industry, :website)
                    ON DUPLICATE KEY UPDATE
                      company_name = VALUES(company_name),
                      sector = VALUES(sector),
                      industry = VALUES(industry),
                      website = VALUES(website)
                    """
                ),
                {
                    "ticker": ticker,
                    "company_name": company.get("company_name"),
                    "sector": company.get("sector"),
                    "industry": company.get("industry"),
                    "website": company.get("website"),
                },
            )
            self._insert_analysis_run(conn, run_id, ticker, state, decision)
            self._insert_agent_outputs(conn, run_id, state)
            self._insert_market_snapshot(conn, run_id, ticker, market)
            self._insert_company_profile(conn, run_id, ticker, company)
            self._insert_financial_metrics(conn, run_id, ticker, financial)
            self._insert_news_items(conn, run_id, ticker, news)
            self._insert_technical_indicators(conn, run_id, ticker, technical)
            self._insert_risk_assessment(conn, run_id, ticker, decision)
            self._insert_decision(conn, run_id, ticker, decision)
            self._insert_reflection(conn, run_id, reflection)
            self._insert_final_report(conn, run_id, ticker, state)
            self._insert_audit_events(conn, run_id, state.get("audit_log", []))

        return run_id

    def _insert_analysis_run(self, conn: Any, run_id: str, ticker: str, state: dict, decision: dict) -> None:
        conn.execute(
            text(
                """
                INSERT INTO analysis_runs (
                  id, ticker, user_request, as_of_date, status, confidence_score,
                  confidence_threshold, max_retries, retry_count, rating, risk_score,
                  risk_level, final_report_path
                )
                VALUES (
                  :id, :ticker, :user_request, :as_of_date, 'completed', :confidence_score,
                  :confidence_threshold, :max_retries, :retry_count, :rating, :risk_score,
                  :risk_level, :final_report_path
                )
                """
            ),
            {
                "id": run_id,
                "ticker": ticker,
                "user_request": state.get("user_request", ""),
                "as_of_date": state.get("as_of_date"),
                "confidence_score": _decimal(state.get("confidence_score")),
                "confidence_threshold": _decimal(state.get("confidence_threshold")),
                "max_retries": int(state.get("max_retries", 1)),
                "retry_count": int(state.get("retry_count", 0)),
                "rating": decision.get("rating"),
                "risk_score": _int(decision.get("risk_score")),
                "risk_level": decision.get("risk_level"),
                "final_report_path": state.get("final_report_path"),
            },
        )

    def _insert_agent_outputs(self, conn: Any, run_id: str, state: dict) -> None:
        sections = [
            ("planner", "planner_tasks", state.get("planner_tasks", {})),
            ("company_agent", "company_profile", state.get("company_profile", {})),
            ("financial_agent", "financial_metrics", state.get("financial_metrics", {})),
            ("news_agent", "news_sentiment", state.get("news_sentiment", {})),
            ("technical_agent", "technical_indicators", state.get("technical_indicators", {})),
            ("decision_agent", "decision_summary", state.get("decision_summary", {})),
            ("backtest_agent", "backtest_result", state.get("backtest_result", {})),
            ("reflection_agent", "reflection_result", state.get("reflection_result", {})),
        ]
        for agent_name, output_type, payload in sections:
            conn.execute(
                text(
                    """
                    INSERT INTO agent_outputs (run_id, agent_name, output_type, payload, warnings, sources)
                    VALUES (:run_id, :agent_name, :output_type, :payload, :warnings, :sources)
                    """
                ),
                {
                    "run_id": run_id,
                    "agent_name": agent_name,
                    "output_type": output_type,
                    "payload": _json(payload),
                    "warnings": _json(payload.get("warnings", []) if isinstance(payload, dict) else []),
                    "sources": _json(payload.get("sources", []) if isinstance(payload, dict) else []),
                },
            )

    def _insert_market_snapshot(self, conn: Any, run_id: str, ticker: str, market: dict) -> None:
        indicators = market.get("technical_indicators", {})
        conn.execute(
            text(
                """
                INSERT INTO market_snapshots (
                  run_id, ticker, price, volume, ma20, ma60, return_20d,
                  volatility_20d, trend, indicators, sources
                )
                VALUES (
                  :run_id, :ticker, :price, :volume, :ma20, :ma60, :return_20d,
                  :volatility_20d, :trend, :indicators, :sources
                )
                """
            ),
            {
                "run_id": run_id,
                "ticker": ticker,
                "price": _decimal(market.get("price")),
                "volume": _int(market.get("volume")),
                "ma20": _decimal(indicators.get("ma20")),
                "ma60": _decimal(indicators.get("ma60")),
                "return_20d": _decimal(indicators.get("return_20d")),
                "volatility_20d": _decimal(indicators.get("volatility_20d")),
                "trend": indicators.get("trend"),
                "indicators": _json(indicators),
                "sources": _json(market.get("sources", [])),
            },
        )

    def _insert_company_profile(self, conn: Any, run_id: str, ticker: str, company: dict) -> None:
        conn.execute(
            text(
                """
                INSERT INTO company_profiles (
                  run_id, ticker, company_name, sector, industry, market_cap,
                  business_summary, main_products, key_risks, raw_payload
                )
                VALUES (
                  :run_id, :ticker, :company_name, :sector, :industry, :market_cap,
                  :business_summary, :main_products, :key_risks, :raw_payload
                )
                """
            ),
            {
                "run_id": run_id,
                "ticker": ticker,
                "company_name": company.get("company_name"),
                "sector": company.get("sector"),
                "industry": company.get("industry"),
                "market_cap": _decimal(company.get("market_cap")),
                "business_summary": company.get("business_summary"),
                "main_products": _json(company.get("main_products", [])),
                "key_risks": _json(company.get("key_risks", [])),
                "raw_payload": _json(company),
            },
        )

    def _insert_financial_metrics(self, conn: Any, run_id: str, ticker: str, financial: dict) -> None:
        conn.execute(
            text(
                """
                INSERT INTO financial_metrics (
                  run_id, ticker, revenue, net_income, roe, debt_to_asset,
                  gross_margin, operating_cashflow, cash_flow_quality,
                  financial_risks, raw_payload
                )
                VALUES (
                  :run_id, :ticker, :revenue, :net_income, :roe, :debt_to_asset,
                  :gross_margin, :operating_cashflow, :cash_flow_quality,
                  :financial_risks, :raw_payload
                )
                """
            ),
            {
                "run_id": run_id,
                "ticker": ticker,
                "revenue": _decimal(financial.get("revenue")),
                "net_income": _decimal(financial.get("net_income")),
                "roe": _decimal(financial.get("roe")),
                "debt_to_asset": _decimal(financial.get("debt_to_asset")),
                "gross_margin": _decimal(financial.get("gross_margin")),
                "operating_cashflow": _decimal(financial.get("operating_cashflow")),
                "cash_flow_quality": _decimal(financial.get("cash_flow_quality")),
                "financial_risks": _json(financial.get("financial_risks", [])),
                "raw_payload": _json(financial),
            },
        )

    def _insert_news_items(self, conn: Any, run_id: str, ticker: str, news: dict) -> None:
        for item in news.get("items", []):
            conn.execute(
                text(
                    """
                    INSERT INTO news_items (
                      run_id, ticker, title, publisher, link, published_at,
                      sentiment, labels, raw_payload
                    )
                    VALUES (
                      :run_id, :ticker, :title, :publisher, :link, :published_at,
                      :sentiment, :labels, :raw_payload
                    )
                    """
                ),
                {
                    "run_id": run_id,
                    "ticker": ticker,
                    "title": item.get("title", ""),
                    "publisher": item.get("publisher"),
                    "link": item.get("link"),
                    "published_at": _parse_datetime(item.get("published_at")),
                    "sentiment": item.get("sentiment"),
                    "labels": _json(item.get("labels", [])),
                    "raw_payload": _json(item),
                },
            )

    def _insert_technical_indicators(
        self, conn: Any, run_id: str, ticker: str, technical: dict
    ) -> None:
        market = technical.get("market_snapshot", {})
        indicators = market.get("technical_indicators", {})
        support_resistance = technical.get("support_resistance", {})
        conn.execute(
            text(
                """
                INSERT INTO technical_indicators (
                  run_id, ticker, trend, volume_signal, macd_signal, rsi_signal,
                  valuation_pe, valuation_pb, support, resistance, indicators,
                  technical_risks, warnings, raw_payload
                )
                VALUES (
                  :run_id, :ticker, :trend, :volume_signal, :macd_signal, :rsi_signal,
                  :valuation_pe, :valuation_pb, :support, :resistance, :indicators,
                  :technical_risks, :warnings, :raw_payload
                )
                """
            ),
            {
                "run_id": run_id,
                "ticker": ticker,
                "trend": technical.get("trend"),
                "volume_signal": technical.get("volume_signal"),
                "macd_signal": technical.get("macd_signal"),
                "rsi_signal": technical.get("rsi_signal"),
                "valuation_pe": _decimal(technical.get("valuation_pe")),
                "valuation_pb": _decimal(technical.get("valuation_pb")),
                "support": _decimal(support_resistance.get("support")),
                "resistance": _decimal(support_resistance.get("resistance")),
                "indicators": _json(indicators),
                "technical_risks": _json(technical.get("technical_risks", [])),
                "warnings": _json(technical.get("warnings", [])),
                "raw_payload": _json(technical),
            },
        )

    def _insert_risk_assessment(self, conn: Any, run_id: str, ticker: str, decision: dict) -> None:
        conn.execute(
            text(
                """
                INSERT INTO risk_assessments (
                  run_id, ticker, risk_score, risk_level, risk_points, warnings, raw_payload
                )
                VALUES (
                  :run_id, :ticker, :risk_score, :risk_level, :risk_points,
                  :warnings, :raw_payload
                )
                """
            ),
            {
                "run_id": run_id,
                "ticker": ticker,
                "risk_score": _int(decision.get("risk_score")),
                "risk_level": decision.get("risk_level"),
                "risk_points": _json(decision.get("risk_points", [])),
                "warnings": _json(decision.get("warnings", [])),
                "raw_payload": _json(decision),
            },
        )

    def _insert_decision(self, conn: Any, run_id: str, ticker: str, decision: dict) -> None:
        conn.execute(
            text(
                """
                INSERT INTO decision_summaries (
                  run_id, ticker, rating, confidence, risk_score, supporting_points,
                  risk_points, warnings, raw_payload
                )
                VALUES (
                  :run_id, :ticker, :rating, :confidence, :risk_score,
                  :supporting_points, :risk_points, :warnings, :raw_payload
                )
                """
            ),
            {
                "run_id": run_id,
                "ticker": ticker,
                "rating": decision.get("rating"),
                "confidence": _decimal(decision.get("confidence")),
                "risk_score": _int(decision.get("risk_score")),
                "supporting_points": _json(decision.get("supporting_points", [])),
                "risk_points": _json(decision.get("risk_points", [])),
                "warnings": _json(decision.get("warnings", [])),
                "raw_payload": _json(decision),
            },
        )

    def _insert_reflection(self, conn: Any, run_id: str, reflection: dict) -> None:
        conn.execute(
            text(
                """
                INSERT INTO reflection_reviews (
                  run_id, passed, completeness_score, logic_score, risk_coverage_score,
                  missing_items, retry_tasks, review_comment, raw_payload
                )
                VALUES (
                  :run_id, :passed, :completeness_score, :logic_score, :risk_coverage_score,
                  :missing_items, :retry_tasks, :review_comment, :raw_payload
                )
                """
            ),
            {
                "run_id": run_id,
                "passed": bool(reflection.get("passed", False)),
                "completeness_score": _decimal(reflection.get("completeness_score")),
                "logic_score": _decimal(reflection.get("logic_score")),
                "risk_coverage_score": _decimal(reflection.get("risk_coverage_score")),
                "missing_items": _json(reflection.get("missing_items", [])),
                "retry_tasks": _json(reflection.get("retry_tasks", [])),
                "review_comment": reflection.get("review_comment"),
                "raw_payload": _json(reflection),
            },
        )

    def _insert_final_report(self, conn: Any, run_id: str, ticker: str, state: dict) -> None:
        conn.execute(
            text(
                """
                INSERT INTO final_reports (run_id, ticker, report_path, report_markdown)
                VALUES (:run_id, :ticker, :report_path, :report_markdown)
                """
            ),
            {
                "run_id": run_id,
                "ticker": ticker,
                "report_path": state.get("final_report_path"),
                "report_markdown": state.get("final_report", ""),
            },
        )

    def _insert_audit_events(self, conn: Any, run_id: str, events: list[dict]) -> None:
        for event in events:
            conn.execute(
                text(
                    """
                    INSERT INTO audit_events (run_id, agent_name, message, payload, event_time)
                    VALUES (:run_id, :agent_name, :message, :payload, :event_time)
                    """
                ),
                {
                    "run_id": run_id,
                    "agent_name": event.get("agent"),
                    "message": event.get("message", ""),
                    "payload": _json(event.get("payload")),
                    "event_time": _parse_datetime(event.get("timestamp")),
                },
            )
