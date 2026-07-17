"""Read previously ingested local finance data from MySQL."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import text

from multiple_agent_finance.storage.mysql_store import DatabaseStore


def _loads(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _iso_date(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    return str(value)


def _iso_datetime(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def load_latest_company_profile(ticker: str) -> dict[str, Any] | None:
    """Return the latest locally persisted company profile payload."""

    normalized = ticker.upper()
    with DatabaseStore().engine.connect() as conn:
        row = (
            conn.execute(
                text(
                    """
                    SELECT *
                    FROM company_profiles
                    WHERE ticker = :ticker
                    ORDER BY created_at DESC, id DESC
                    LIMIT 1
                    """
                ),
                {"ticker": normalized},
            )
            .mappings()
            .first()
        )

    if not row:
        return None

    raw_payload = _loads(row.get("raw_payload")) if row.get("raw_payload") else {}
    payload = raw_payload if isinstance(raw_payload, dict) else {}
    payload.update(
        {
            "ticker": normalized,
            "company_name": payload.get("company_name") or row.get("company_name") or normalized,
            "sector": payload.get("sector") or row.get("sector"),
            "industry": payload.get("industry") or row.get("industry"),
            "market_cap": payload.get("market_cap") or _as_float(row.get("market_cap")),
            "business_summary": payload.get("business_summary") or row.get("business_summary"),
            "main_products": payload.get("main_products") or _loads(row.get("main_products")) or [],
            "key_risks": payload.get("key_risks") or _loads(row.get("key_risks")) or [],
            "warnings": list(payload.get("warnings", [])),
            "sources": [{"type": "company_profile", "name": "local_mysql"}],
        }
    )
    return payload


def load_latest_quarterly_financials(ticker: str) -> dict[str, Any] | None:
    """Return latest four-quarter financial rows grouped by statement/date."""

    normalized = ticker.upper()
    with DatabaseStore().engine.connect() as conn:
        run_id = conn.execute(
            text(
                """
                SELECT run_id
                FROM financial_quarterly_metrics
                WHERE ticker = :ticker
                GROUP BY run_id
                ORDER BY MAX(created_at) DESC
                LIMIT 1
                """
            ),
            {"ticker": normalized},
        ).scalar()
        if not run_id:
            return None

        rows = (
            conn.execute(
                text(
                    """
                    SELECT statement_type, fiscal_date, metric_name, metric_value, raw_value, source
                    FROM financial_quarterly_metrics
                    WHERE ticker = :ticker AND run_id = :run_id
                    ORDER BY fiscal_date DESC, statement_type, metric_name
                    """
                ),
                {"ticker": normalized, "run_id": run_id},
            )
            .mappings()
            .all()
        )

    if not rows:
        return None

    statements: dict[str, dict[str, dict[str, float | None]]] = {}
    flat_rows: list[dict[str, Any]] = []
    quarters: list[str] = []
    for row in rows:
        fiscal_date = _iso_date(row.get("fiscal_date"))
        if not fiscal_date:
            continue
        if fiscal_date not in quarters:
            quarters.append(fiscal_date)
        statement_type = str(row.get("statement_type"))
        metric_name = str(row.get("metric_name"))
        value = _as_float(row.get("metric_value"))
        statements.setdefault(statement_type, {}).setdefault(fiscal_date, {})[metric_name] = value
        flat_rows.append(
            {
                "statement_type": statement_type,
                "fiscal_date": fiscal_date,
                "metric_name": metric_name,
                "metric_value": value,
                "raw_value": row.get("raw_value"),
                "source": row.get("source") or "local_mysql",
            }
        )

    return {
        "run_id": run_id,
        "quarters": quarters[:4],
        "statements": statements,
        "rows": flat_rows,
        "row_count": len(flat_rows),
        "sources": [{"type": "financial_quarterly_metrics", "name": "local_mysql"}],
    }


def load_daily_top_news(
    ticker: str,
    as_of_date: str | None = None,
    *,
    lookback_days: int = 365,
) -> dict[str, Any] | None:
    """Return the latest locally persisted one-news-per-day dataset."""

    normalized = ticker.upper()
    end_date = date.today()
    if as_of_date:
        try:
            end_date = datetime.fromisoformat(as_of_date).date()
        except ValueError:
            end_date = date.today()
    start_date = end_date - timedelta(days=lookback_days)

    with DatabaseStore().engine.connect() as conn:
        run_id = conn.execute(
            text(
                """
                SELECT run_id
                FROM news_daily_top_items
                WHERE ticker = :ticker
                GROUP BY run_id
                ORDER BY MAX(created_at) DESC
                LIMIT 1
                """
            ),
            {"ticker": normalized},
        ).scalar()
        if not run_id:
            return None

        rows = (
            conn.execute(
                text(
                    """
                    SELECT news_date, rank_no, title, publisher, link, published_at,
                           source, query_text, raw_payload
                    FROM news_daily_top_items
                    WHERE ticker = :ticker
                      AND run_id = :run_id
                      AND news_date BETWEEN :start_date AND :end_date
                    ORDER BY news_date, rank_no
                    """
                ),
                {
                    "ticker": normalized,
                    "run_id": run_id,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
            )
            .mappings()
            .all()
        )

    if not rows:
        return None

    items = [
        {
            "news_date": _iso_date(row.get("news_date")),
            "rank_no": int(row.get("rank_no") or 1),
            "title": row.get("title") or "",
            "publisher": row.get("publisher"),
            "link": row.get("link"),
            "published_at": _iso_datetime(row.get("published_at")),
            "source": row.get("source") or "local_mysql",
            "query_text": row.get("query_text"),
            "raw_payload": _loads(row.get("raw_payload")),
        }
        for row in rows
    ]
    dates = [item["news_date"] for item in items if item.get("news_date")]
    return {
        "run_id": run_id,
        "items": items,
        "coverage": {
            "start_date": min(dates) if dates else None,
            "end_date": max(dates) if dates else None,
            "days_with_results": len(set(dates)),
            "items": len(items),
            "policy": "one most relevant item per day",
        },
        "sources": [{"type": "news_daily_top_items", "name": "local_mysql"}],
    }
