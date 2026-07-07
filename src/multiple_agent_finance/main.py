"""Command line entry for the multi-agent finance workflow."""

from __future__ import annotations

import argparse
import json
from datetime import date
from typing import Any

from multiple_agent_finance.graph.builder import build_graph


def run_analysis(
    ticker: str,
    user_request: str,
    *,
    as_of_date: str | None = None,
    confidence_threshold: float = 0.75,
    max_retries: int = 1,
) -> dict[str, Any]:
    """Run the LangGraph workflow and return the final state."""

    graph = build_graph()
    initial_state = {
        "ticker": ticker.upper(),
        "user_request": user_request,
        "as_of_date": as_of_date or date.today().isoformat(),
        "retry_count": 0,
        "max_retries": max_retries,
        "confidence_threshold": confidence_threshold,
        "shared_memory_refs": [],
        "knowledge_base_refs": [],
        "external_data_refs": [],
        "audit_log": [],
    }
    return graph.invoke(initial_state)


def save_to_database(result: dict[str, Any]) -> str:
    """Persist a completed analysis run into MySQL."""

    from multiple_agent_finance.storage.mysql_store import DatabaseStore

    return DatabaseStore().save_analysis_state(result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the LangGraph multi-agent stock analysis.")
    parser.add_argument("--ticker", default="AAPL", help="Stock ticker, e.g. AAPL or MSFT.")
    parser.add_argument(
        "--request",
        default="综合分析股票基本面、市场表现、新闻情绪和风险，并给出保守决策摘要。",
        help="User analysis request.",
    )
    parser.add_argument("--date", dest="as_of_date", default=None, help="Analysis date.")
    parser.add_argument("--threshold", type=float, default=0.75, help="Confidence threshold.")
    parser.add_argument("--max-retries", type=int, default=1, help="Maximum reflection retries.")
    parser.add_argument("--json", action="store_true", help="Print final state as JSON.")
    parser.add_argument("--save-db", action="store_true", help="Persist analysis result to MySQL.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = run_analysis(
        args.ticker,
        args.request,
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
    print(f"\n报告已保存: {result.get('final_report_path')}")
    if args.save_db:
        print(f"数据库运行 ID: {result.get('database_run_id')}")


if __name__ == "__main__":
    main()
