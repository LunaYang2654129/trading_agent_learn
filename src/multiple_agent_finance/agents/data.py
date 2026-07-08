"""Data Collection Agent for the weekly technical single-link workflow."""

from __future__ import annotations

from multiple_agent_finance.agents.base import audit_event
from multiple_agent_finance.graph.state import StockAnalysisState
from multiple_agent_finance.tools.data_tools import collect_market_data


def data_collection_agent_node(state: StockAnalysisState) -> dict:
    """Collect OHLCV data and optionally persist raw market bars before planning."""

    ticker = state["ticker"].upper()
    period = state.get("market_period", "1y")
    market_data = collect_market_data(
        ticker,
        as_of_date=state.get("as_of_date"),
        period=period,
    )
    records = market_data.get("records", [])
    ingestion = {
        "ticker": ticker,
        "source": "yfinance",
        "persisted": False,
        "rows_collected": len(records),
        "rows_persisted": 0,
        "warnings": list(market_data.get("warnings", [])),
    }

    if state.get("persist_data"):
        try:
            from multiple_agent_finance.storage.mysql_store import DatabaseStore

            ingestion["rows_persisted"] = DatabaseStore().save_market_data(market_data)
            ingestion["persisted"] = True
        except Exception as exc:
            ingestion["warnings"].append(f"行情数据入库失败: {exc}")

    return {
        "market_data": market_data,
        "data_ingestion_result": ingestion,
        "external_data_refs": market_data.get("sources", []),
        "audit_log": [audit_event("data_collection_agent", "market data collected", ingestion)],
    }
