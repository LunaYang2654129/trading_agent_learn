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


def _prediction_text(state: StockAnalysisState) -> list[str]:
    technical = state.get("technical_indicators", {})
    snapshot = technical.get("market_snapshot", {})
    indicators = snapshot.get("technical_indicators", {})
    support_resistance = technical.get("support_resistance", {})
    trend = technical.get("trend", "unknown")
    macd_signal = technical.get("macd_signal", "unknown")
    rsi_signal = technical.get("rsi_signal", "unknown")
    volume_signal = technical.get("volume_signal", "unknown")
    price = indicators.get("latest_close")
    ma20 = indicators.get("ma20")
    support = support_resistance.get("support")
    resistance = support_resistance.get("resistance")

    if macd_signal == "bullish" and rsi_signal in {"neutral", "oversold"}:
        bias = "短线存在修复动能，但仍需要突破压力位确认。"
    elif trend == "bearish" or macd_signal == "bearish":
        bias = "短线偏弱，优先观察支撑位是否有效。"
    else:
        bias = "短线大概率维持震荡，需要等待量价方向进一步确认。"

    return [
        f"- 最新收盘价：{_format_num(price)}",
        f"- MA20：{_format_num(ma20)}",
        f"- 支撑位：{_format_num(support)}",
        f"- 压力位：{_format_num(resistance)}",
        f"- 趋势判断：{trend}",
        f"- 量能信号：{volume_signal}",
        f"- MACD 信号：{macd_signal}",
        f"- RSI 信号：{rsi_signal}",
        f"- 预测结论：{bias}",
    ]


def _format_report(state: StockAnalysisState) -> str:
    decision = state.get("decision_summary", {})
    reflection = state.get("reflection_result", {})
    technical = state.get("technical_indicators", {})
    snapshot = technical.get("market_snapshot", {})
    indicators = snapshot.get("technical_indicators", {})
    ticker = state.get("ticker", "UNKNOWN")
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    chain_mode = state.get("chain_mode", "technical")

    sections = [
        f"# {ticker} 单链路多智能体技术预测报告",
        "",
        f"生成时间：{generated_at}",
        f"分析日期：{state.get('as_of_date', '未指定')}",
        f"链路模式：{chain_mode}",
        f"用户需求：{state.get('user_request', '未指定')}",
        "",
        "## 1. 决策摘要",
        "",
        f"- 评级：{decision.get('rating', 'unknown')}",
        f"- 风险等级：{decision.get('risk_level', 'unknown')}",
        f"- 风险分数：{decision.get('risk_score', 'unknown')}",
        f"- 置信度：{state.get('confidence_score', 0):.2f}",
        f"- 反思结论：{reflection.get('review_comment', '未生成')}",
        "",
        "## 2. 单股预测结论",
        "",
        *_prediction_text(state),
        "",
        "## 3. 技术指标摘要",
        "",
        f"- 20 日收益率：{_format_pct(indicators.get('return_20d'))}",
        f"- MACD：{_format_num(indicators.get('macd'), 4)}",
        f"- MACD 信号线：{_format_num(indicators.get('macd_signal_line'), 4)}",
        f"- MACD 柱：{_format_num(indicators.get('macd_histogram'), 4)}",
        f"- RSI14：{_format_num(indicators.get('rsi14'))}",
        f"- 布林带中轨：{_format_num(indicators.get('boll'))}",
        f"- 布林带上轨：{_format_num(indicators.get('boll_ub'))}",
        f"- 布林带下轨：{_format_num(indicators.get('boll_lb'))}",
        f"- ATR14：{_format_num(indicators.get('atr14'))}",
        f"- 20 日平均成交量：{_format_num(indicators.get('avg_volume_20d'), 0)}",
        "",
        "## 4. 支撑观点",
        "",
        _json_block(decision.get("supporting_points", [])),
        "",
        "## 5. 风险点",
        "",
        _json_block(decision.get("risk_points", [])),
        "",
    ]

    if state.get("market_data") or state.get("data_ingestion_result"):
        sections.extend(
            [
                "## 6. 数据来源与样本范围",
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
                "",
            ]
        )

    sections.extend(
        [
            "## 7. Technical Agent 原始输出",
            "",
            _json_block(technical),
            "",
            "## 8. Reflection 校验",
            "",
            _json_block(reflection),
            "",
            "## 9. 审计日志",
            "",
            _json_block(state.get("audit_log", [])),
            "",
            "## 10. 使用边界",
            "",
            "本报告只验证本周最小单链路的可行性，当前只包含技术面数据，不包含公司基本面、财务、新闻舆情和独立风险 Agent。结论不构成投资建议。",
            "",
        ]
    )
    return "\n".join(sections)


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
