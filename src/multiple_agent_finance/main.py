"""Command line entry for the multi-agent finance workflow."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Literal

from multiple_agent_finance.graph.builder import build_graph
from multiple_agent_finance.graph.technical_chain import build_technical_chain_graph


DEFAULT_REQUEST = (
    "Analyze company fundamentals, market behavior, news sentiment, and risks. "
    "Return a conservative decision summary."
)
TECHNICAL_REQUEST = (
    "Run the weekly technical single-link plan: use preloaded market data, "
    "analyze technical indicators, make a single-stock prediction, and validate the result."
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
    backtest_horizons: tuple[int, ...] | None = None,
    backtest_lookback_days: int | None = None,
    market_data: dict[str, Any] | None = None,
    data_ingestion_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = {
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
    if backtest_horizons is not None:
        state["backtest_horizons"] = list(backtest_horizons)
    if backtest_lookback_days is not None:
        state["backtest_lookback_days"] = backtest_lookback_days
    if market_data is not None:
        state["market_data"] = market_data
        state["data_ingestion_result"] = data_ingestion_result or {
            "ticker": ticker.upper(),
            "source": "preloaded_csv",
            "persisted": False,
            "rows_collected": len(market_data.get("records", [])),
            "rows_persisted": 0,
            "warnings": list(market_data.get("warnings", [])),
        }
    return state


def _float_or_none(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def parse_backtest_horizons(value: str | None) -> tuple[int, ...] | None:
    """Parse a comma-separated horizon list such as ``1,3,5``."""

    if value in (None, ""):
        return None
    horizons: list[int] = []
    for raw_item in value.split(","):
        item = raw_item.strip()
        if not item:
            continue
        try:
            horizon = int(item)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                "backtest horizons must be comma-separated positive integers"
            ) from exc
        if horizon <= 0:
            raise argparse.ArgumentTypeError("backtest horizons must be positive integers")
        horizons.append(horizon)
    if not horizons:
        raise argparse.ArgumentTypeError("at least one backtest horizon is required")
    return tuple(horizons)


def load_market_data_csv(
    path: str | Path,
    *,
    ticker: str,
    as_of_date: str | None = None,
    period: str = "custom",
) -> dict[str, Any]:
    """Load pre-collected OHLCV CSV data for Technical Agent input."""

    csv_path = Path(path)
    records: list[dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            volume = _int_or_none(row.get("volume"))
            volume_lots = _int_or_none(row.get("volume_lots"))
            if volume is None and volume_lots is not None:
                volume = volume_lots * 100
            records.append(
                {
                    "date": row.get("date"),
                    "open": _float_or_none(row.get("open")),
                    "high": _float_or_none(row.get("high")),
                    "low": _float_or_none(row.get("low")),
                    "close": _float_or_none(row.get("close")),
                    "volume": volume,
                }
            )

    return {
        "ticker": ticker.upper(),
        "as_of_date": as_of_date,
        "period": period,
        "records": records,
        "valuation_pe": None,
        "valuation_pb": None,
        "warnings": [],
        "sources": [{"type": "csv", "name": str(csv_path)}],
    }


def run_analysis(
    ticker: str,
    user_request: str,
    *,
    as_of_date: str | None = None,
    confidence_threshold: float = 0.75,
    max_retries: int = 1,
    backtest_horizons: tuple[int, ...] | None = None,
    backtest_lookback_days: int | None = None,
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
            backtest_horizons=backtest_horizons,
            backtest_lookback_days=backtest_lookback_days,
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
    backtest_horizons: tuple[int, ...] | None = None,
    backtest_lookback_days: int | None = None,
    market_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the weekly technical single-link workflow and return the final state."""

    data_ingestion_result = None
    if market_data is None:
        from multiple_agent_finance.tools.data_tools import collect_market_data

        market_data = collect_market_data(
            ticker,
            as_of_date=as_of_date,
            period=market_period,
        )
        data_ingestion_result = {
            "ticker": ticker.upper(),
            "source": "yfinance",
            "persisted": False,
            "rows_collected": len(market_data.get("records", [])),
            "rows_persisted": 0,
            "warnings": list(market_data.get("warnings", [])),
        }
        if persist_data:
            try:
                data_ingestion_result["rows_persisted"] = int(
                    save_to_database_market_data(market_data)
                )
                data_ingestion_result["persisted"] = True
            except Exception as exc:
                data_ingestion_result["warnings"].append(f"Market data persistence failed: {exc}")
    elif persist_data:
        data_ingestion_result = {
            "ticker": ticker.upper(),
            "source": "preloaded_csv",
            "persisted": False,
            "rows_collected": len(market_data.get("records", [])),
            "rows_persisted": 0,
            "warnings": list(market_data.get("warnings", [])),
        }
        try:
            data_ingestion_result["rows_persisted"] = int(
                save_to_database_market_data(market_data)
            )
            data_ingestion_result["persisted"] = True
        except Exception as exc:
            data_ingestion_result["warnings"].append(f"Market data persistence failed: {exc}")

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
            backtest_horizons=backtest_horizons,
            backtest_lookback_days=backtest_lookback_days,
            market_data=market_data,
            data_ingestion_result=data_ingestion_result,
        )
    )


def save_to_database(result: dict[str, Any]) -> str:
    """Persist a completed analysis run into MySQL."""

    from multiple_agent_finance.storage.mysql_store import DatabaseStore

    return DatabaseStore().save_analysis_state(result)


def save_to_database_market_data(market_data: dict[str, Any]) -> int:
    """Persist collected market bars into MySQL."""

    from multiple_agent_finance.storage.mysql_store import DatabaseStore

    return DatabaseStore().save_market_data(market_data)


def _database_error_message(error: Exception) -> str:
    from multiple_agent_finance.config.settings import settings

    return (
        "Database save failed. Could not connect to MySQL at "
        f"{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}. "
        "Start MySQL with `powershell -ExecutionPolicy Bypass -File scripts/start_mysql.ps1`, "
        "initialize it with `powershell -ExecutionPolicy Bypass -File "
        "scripts/init_mysql_database.ps1`, or rerun without `--save-db`. "
        f"Original error: {error}"
    )


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
        "--backtest-horizons",
        type=parse_backtest_horizons,
        default=None,
        help="Comma-separated forward-return horizons, e.g. 1,3,5. Defaults to 1,5,10.",
    )
    parser.add_argument(
        "--backtest-lookback-days",
        type=int,
        default=None,
        help="Calendar-day lookback window for backtest metrics. Defaults to 183.",
    )
    parser.add_argument(
        "--market-data-csv",
        default=None,
        help="Pre-collected OHLCV CSV for the technical single-link graph.",
    )
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
        market_data = (
            load_market_data_csv(
                args.market_data_csv,
                ticker=args.ticker,
                as_of_date=args.as_of_date,
                period=args.market_period,
            )
            if args.market_data_csv
            else None
        )
        result = run_technical_chain(
            args.ticker,
            args.request or TECHNICAL_REQUEST,
            as_of_date=args.as_of_date,
            confidence_threshold=args.threshold,
            max_retries=args.max_retries,
            market_period=args.market_period,
            persist_data=args.persist_data,
            backtest_horizons=args.backtest_horizons,
            backtest_lookback_days=args.backtest_lookback_days,
            market_data=market_data,
        )
    else:
        result = run_analysis(
            args.ticker,
            args.request or DEFAULT_REQUEST,
            as_of_date=args.as_of_date,
            confidence_threshold=args.threshold,
            max_retries=args.max_retries,
            backtest_horizons=args.backtest_horizons,
            backtest_lookback_days=args.backtest_lookback_days,
        )

    database_error = None
    if args.save_db:
        try:
            result["database_run_id"] = save_to_database(result)
        except Exception as exc:
            database_error = _database_error_message(exc)
            result["database_error"] = database_error

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        if database_error:
            raise SystemExit(1)
        return

    print(result["final_report"])
    print(f"\nReport saved: {result.get('final_report_path')}")
    if result.get("audit_report_path"):
        print(f"Audit report saved: {result.get('audit_report_path')}")
    if database_error:
        print(f"\n{database_error}", file=sys.stderr)
        raise SystemExit(1)
    if args.save_db:
        print(f"Database run ID: {result.get('database_run_id')}")


if __name__ == "__main__":
    main()
