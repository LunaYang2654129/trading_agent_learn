"""Final report and audit-log document generation nodes."""

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


def _format_pct(value: Any) -> str:
    try:
        if value is None:
            return "未知"
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return "未知"


def _format_num(value: Any, digits: int = 2) -> str:
    try:
        if value is None:
            return "未知"
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "未知"


def _technical_lines(state: StockAnalysisState) -> list[str]:
    technical = state.get("technical_indicators", {})
    snapshot = technical.get("market_snapshot", {})
    indicators = snapshot.get("technical_indicators", {})
    support_resistance = technical.get("support_resistance", {})
    return [
        f"- 最新收盘价：{_format_num(indicators.get('latest_close'))}",
        f"- 趋势判断：{technical.get('trend', 'unknown')}",
        f"- 量能信号：{technical.get('volume_signal', 'unknown')}",
        f"- MACD 信号：{technical.get('macd_signal', 'unknown')}",
        f"- RSI 信号：{technical.get('rsi_signal', 'unknown')}",
        f"- MA20：{_format_num(indicators.get('ma20'))}",
        f"- 20 日收益率：{_format_pct(indicators.get('return_20d'))}",
        f"- 支撑位：{_format_num(support_resistance.get('support'))}",
        f"- 压力位：{_format_num(support_resistance.get('resistance'))}",
    ]


def _backtest_lines(state: StockAnalysisState) -> list[str]:
    backtest = state.get("backtest_result", {})
    window = backtest.get("window", {})
    metrics = backtest.get("metrics", {})
    horizons = backtest.get("horizons") or [
        int(str(key).removesuffix("d"))
        for key in metrics
        if str(key).endswith("d") and str(key).removesuffix("d").isdigit()
    ]
    lines = [
        "## 收益率回测",
        "",
        f"- 方法：{backtest.get('method', 'forward_return_event_study')}",
        f"- 前瞻交易日：{'/'.join(str(horizon) for horizon in horizons)}",
        f"- 区间：{window.get('start_date', '未知')} 至 {window.get('end_date', '未知')}",
        f"- 样本交易日：{window.get('bar_count', 0)}",
        "",
        "| 指标 | 样本数 | 平均收益 | 中位数 | 最小值 | 最大值 | 胜率 | 最新可计算收益 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for horizon in horizons:
        key = f"{horizon}d"
        row = metrics.get(key, {})
        lines.append(
            "| "
            f"{key} | "
            f"{row.get('count', 0)} | "
            f"{_format_pct(row.get('mean'))} | "
            f"{_format_pct(row.get('median'))} | "
            f"{_format_pct(row.get('min'))} | "
            f"{_format_pct(row.get('max'))} | "
            f"{_format_pct(row.get('win_rate'))} | "
            f"{_format_pct(row.get('latest_return'))} |"
        )
    warnings = backtest.get("warnings", [])
    if warnings:
        lines.extend(["", "回测警告：", "", _json_block(warnings)])
    return lines


def _full_evidence_sections(state: StockAnalysisState) -> list[str]:
    company = state.get("company_profile", {})
    financial = state.get("financial_metrics", {})
    news = state.get("news_sentiment", {})
    quarterly = financial.get("quarterly_metrics", {})
    coverage = news.get("coverage", {})

    return [
        "## 公司画像",
        "",
        f"- 公司名称：{company.get('company_name', state.get('ticker', 'UNKNOWN'))}",
        f"- 行业/板块：{company.get('sector', '未知')} / {company.get('industry', '未知')}",
        f"- 市值：{_format_num(company.get('market_cap'), 0)}",
        f"- 主要产品：{', '.join(company.get('main_products', [])) or '未知'}",
        "",
        "## 四季度财务摘要",
        "",
        f"- 覆盖季度数：{len(quarterly.get('quarters', []))}",
        f"- 最近季度收入：{_format_num(financial.get('revenue'), 0)}",
        f"- 最近季度净利润：{_format_num(financial.get('net_income'), 0)}",
        f"- ROE：{_format_pct(financial.get('roe'))}",
        f"- 资产负债率：{_format_pct(financial.get('debt_to_asset'))}",
        f"- 毛利率：{_format_pct(financial.get('gross_margin'))}",
        f"- 经营现金流质量：{_format_num(financial.get('cash_flow_quality'))}",
        "",
        "## 过去一年每日新闻摘要",
        "",
        f"- 新闻条数：{len(news.get('items', []))}",
        f"- 覆盖区间：{coverage.get('start_date', '未知')} 至 {coverage.get('end_date', '未知')}",
        f"- 覆盖天数：{coverage.get('days_with_results', '未知')}",
        f"- 情绪分数：{_format_num(news.get('sentiment_score'))}",
        f"- 摘要：{news.get('summary', '新闻摘要不可用')}",
        "",
        "## 技术指标摘要",
        "",
        *_technical_lines(state),
    ]


def _technical_only_sections(state: StockAnalysisState) -> list[str]:
    return [
        "## 单股预测结论",
        "",
        *_technical_lines(state),
        "",
        "## 数据来源与样本范围",
        "",
        _json_block(
            {
                "market_data_summary": {
                    "ticker": state.get("market_data", {}).get("ticker"),
                    "period": state.get("market_data", {}).get("period"),
                    "records": len(state.get("market_data", {}).get("records", [])),
                    "sources": state.get("market_data", {}).get("sources", []),
                    "warnings": state.get("market_data", {}).get("warnings", []),
                },
                "data_ingestion_result": state.get("data_ingestion_result", {}),
            }
        ),
    ]


def _format_report(state: StockAnalysisState, audit_report_path: str) -> str:
    decision = state.get("decision_summary", {})
    reflection = state.get("reflection_result", {})
    ticker = state.get("ticker", "UNKNOWN")
    chain_mode = state.get("chain_mode", "full")
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    audit_count = len(state.get("audit_log", []))

    sections = [
        f"# {ticker} 多智能体股票分析报告",
        "",
        f"生成时间：{generated_at}",
        f"分析日期：{state.get('as_of_date', '未指定')}",
        f"链路模式：{chain_mode}",
        f"用户需求：{state.get('user_request', '未指定')}",
        "",
        "## 决策摘要",
        "",
        f"- 评级：{decision.get('rating', 'unknown')}",
        f"- 风险等级：{decision.get('risk_level', 'unknown')}",
        f"- 风险分数：{decision.get('risk_score', 'unknown')}",
        f"- 置信度：{float(state.get('confidence_score', 0) or 0):.2f}",
        f"- 反思结论：{reflection.get('review_comment', '未生成')}",
        f"- 审计日志：{audit_count} 条，完整文档：{audit_report_path}",
        "",
    ]

    if chain_mode == "technical":
        sections.extend(_technical_only_sections(state))
    else:
        sections.extend(_full_evidence_sections(state))

    sections.extend(
        [
            "",
            *_backtest_lines(state),
            "",
            "## 支撑观点",
            "",
            _json_block(decision.get("supporting_points", [])),
            "",
            "## 风险点",
            "",
            _json_block(decision.get("risk_points", [])),
            "",
            "## Reflection 校验",
            "",
            _json_block(reflection),
            "",
            "## 使用边界",
            "",
            (
                "本报告基于当前可用的公司、财务、新闻、技术和回测数据生成，"
                "不构成投资建议。"
                if chain_mode != "technical"
                else "本报告仅验证技术单链路和半年收益率回测，不包含公司、财务和新闻 Agent 结论，不构成投资建议。"
            ),
            "",
        ]
    )
    return "\n".join(sections)


def _format_audit_report(state: StockAnalysisState) -> str:
    ticker = state.get("ticker", "UNKNOWN")
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    events = state.get("audit_log", [])
    return "\n".join(
        [
            f"# {ticker} 审计日志",
            "",
            f"生成时间：{generated_at}",
            f"事件数量：{len(events)}",
            "",
            "```json",
            _json_block(events),
            "```",
            "",
        ]
    )


def _write_report(ticker: str, content: str, suffix: str = "report") -> Path:
    output_dir = settings.report_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"{ticker.upper()}_{suffix}_{timestamp}.md"
    path.write_text(content, encoding="utf-8")
    return path


def final_report_node(state: StockAnalysisState) -> dict:
    audit_report = _format_audit_report(state)
    audit_report_path = _write_report(state.get("ticker", "UNKNOWN"), audit_report, "audit")
    report = _format_report(state, str(audit_report_path))
    report_path = _write_report(state.get("ticker", "UNKNOWN"), report, "report")
    return {
        "final_report": report,
        "final_report_path": str(report_path),
        "audit_report_path": str(audit_report_path),
        "audit_log": [
            audit_event(
                "final_report",
                "final report and audit report generated",
                {
                    "path": str(report_path),
                    "audit_report_path": str(audit_report_path),
                    "length": len(report),
                    "audit_length": len(audit_report),
                },
            )
        ],
    }
