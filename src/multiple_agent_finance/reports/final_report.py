"""Final report generation node."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from multiple_agent_finance.agents.base import audit_event
from multiple_agent_finance.config.settings import settings
from multiple_agent_finance.graph.state import StockAnalysisState


def _json_block(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def _format_report(state: StockAnalysisState) -> str:
    decision = state.get("decision_summary", {})
    reflection = state.get("reflection_result", {})
    ticker = state.get("ticker", "UNKNOWN")
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""# {ticker} 多智能体股票分析报告

生成时间: {generated_at}
分析日期: {state.get("as_of_date", "未指定")}
用户需求: {state.get("user_request", "未指定")}

## 1. 决策摘要

- 评级: {decision.get("rating", "unknown")}
- 风险等级: {decision.get("risk_level", "unknown")}
- 风险分数: {decision.get("risk_score", "unknown")}
- 置信度: {state.get("confidence_score", 0):.2f}
- 反思结论: {reflection.get("review_comment", "未生成")}

## 2. 支撑观点

{_json_block(decision.get("supporting_points", []))}

## 3. 风险点

{_json_block(decision.get("risk_points", []))}

## 4. 公司画像

{_json_block(state.get("company_profile", {}))}

## 5. 财务分析

{_json_block(state.get("financial_metrics", {}))}

## 6. 新闻舆情

{_json_block(state.get("news_analysis", {}))}

## 7. 行情与风险

{_json_block(state.get("risk_analysis", {}))}

## 8. 反思校验

{_json_block(reflection)}

## 9. 审计日志

{_json_block(state.get("audit_log", []))}
"""


def _write_report(ticker: str, content: str) -> Path:
    output_dir = settings.report_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"{ticker.upper()}_{timestamp}.md"
    path.write_text(content, encoding="utf-8")
    return path


def final_report_node(state: StockAnalysisState) -> dict:
    report = _format_report(state)
    report_path = _write_report(state.get("ticker", "UNKNOWN"), report)
    return {
        "final_report": report,
        "final_report_path": str(report_path),
        "audit_log": [
            audit_event(
                "final_report",
                "final report generated",
                {"path": str(report_path), "length": len(report)},
            )
        ],
    }
