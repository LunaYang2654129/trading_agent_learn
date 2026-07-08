"""Command line entry for the multi-agent finance workflow."""

from __future__ import annotations

import argparse
import json
from datetime import date
from typing import Any, Literal

from multiple_agent_finance.graph.builder import build_graph
from multiple_agent_finance.graph.technical_chain import build_technical_chain_graph


DEFAULT_REQUEST = (
    "Analyze company fundamentals, market behavior, news sentiment, and risks. "
    "Return a conservative decision summary."
)
TECHNICAL_REQUEST = (
    "Run the weekly technical single-link plan: collect data, record ingestion status, "
    "analyze technical indicators, and validate the result."
)


def _base_state(
    ticker: str,
    user_request: str,
    *,
    as_of_date: str | None,
    confidence_threshold: float,
    max_retries: int,
    chain_mode: Literal["full", "technical"],
    market_period: str = "1y",
    persist_data: bool = False,
) -> dict[str, Any]:
    return {
        "ticker": ticker.upper(),
        "user_request": user_request,
        "as_of_date": as_of_date or date.today().isoformat(),
        "retry_count": 0,
        "max_retries": max_retries,
        "confidence_threshold": confidence_threshold,
        "chain_mode": chain_mode,
        "market_period": market_period,
        "persist_data": persist_data,
        "shared_memory_refs": [],
        "knowledge_base_refs": [],
        "external_data_refs": [],
        "audit_log": [],
    }


def run_analysis(
    ticker: str,
    user_request: str,
    *,
    as_of_date: str | None = None,
    confidence_threshold: float = 0.75,
    max_retries: int = 1,
) -> dict[str, Any]:
    """Run the full LangGraph workflow and return the final state."""

    graph = build_graph()
    return graph.invoke(
        _base_state(
            ticker,
            user_request,
            as_of_date=as_of_date,
            confidence_threshold=confidence_threshold,
            max_retries=max_retries,
            chain_mode="full",
        )
    )


def run_technical_chain(
    ticker: str,
    user_request: str = TECHNICAL_REQUEST,
    *,
    as_of_date: str | None = None,
    confidence_threshold: float = 0.75,
    max_retries: int = 1,
    market_period: str = "1y",
    persist_data: bool = False,
) -> dict[str, Any]:
    """Run the weekly technical single-link workflow and return the final state."""

    graph = build_technical_chain_graph()
    return graph.invoke(
        _base_state(
            ticker,
            user_request,
            as_of_date=as_of_date,
            confidence_threshold=confidence_threshold,
            max_retries=max_retries,
            chain_mode="technical",
            market_period=market_period,
            persist_data=persist_data,
        )
    )


def save_to_database(result: dict[str, Any]) -> str:
    """Persist a completed analysis run into MySQL."""

    from multiple_agent_finance.storage.mysql_store import DatabaseStore

    return DatabaseStore().save_analysis_state(result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the LangGraph multi-agent stock analysis.")
    parser.add_argument("--ticker", default="AAPL", help="Stock ticker, e.g. AAPL or MSFT.")
    parser.add_argument(
        "--mode",
        choices=["full", "technical-chain"],
        default="full",
        help="Run the full 7-node graph or the weekly technical single-link graph.",
    )
    parser.add_argument("--request", default=None, help="User analysis request.")
    parser.add_argument("--date", dest="as_of_date", default=None, help="Analysis date.")
    parser.add_argument("--threshold", type=float, default=0.75, help="Confidence threshold.")
    parser.add_argument("--max-retries", type=int, default=1, help="Maximum reflection retries.")
    parser.add_argument("--market-period", default="1y", help="yfinance history period for technical chain.")
    parser.add_argument(
        "--persist-data",
        action="store_true",
        help="Persist collected market bars before running the technical chain.",
    )
    parser.add_argument("--json", action="store_true", help="Print final state as JSON.")
    parser.add_argument("--save-db", action="store_true", help="Persist analysis result to MySQL.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.mode == "technical-chain":
        result = run_technical_chain(
            args.ticker,
            args.request or TECHNICAL_REQUEST,
            as_of_date=args.as_of_date,
            confidence_threshold=args.threshold,
            max_retries=args.max_retries,
            market_period=args.market_period,
            persist_data=args.persist_data,
        )
    else:
        result = run_analysis(
            args.ticker,
            args.request or DEFAULT_REQUEST,
            as_of_date=args.as_of_date,
            confidence_threshold=args.threshold,
            max_retries=args.max_retries,
        )

    if args.save_db:
        result["database_run_id"] = save_to_database(result)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return

    print(result["final_report"])
    print(f"\nReport saved: {result.get('final_report_path')}")
    if args.save_db:
        print(f"Database run ID: {result.get('database_run_id')}")


if __name__ == "__main__":
    main()
