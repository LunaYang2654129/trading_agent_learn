"""News and sentiment tools."""

from __future__ import annotations

from datetime import datetime, timezone


POSITIVE_WORDS = {
    "beat",
    "beats",
    "growth",
    "upgrade",
    "surge",
    "record",
    "profit",
    "positive",
    "strong",
    "outperform",
}
NEGATIVE_WORDS = {
    "miss",
    "downgrade",
    "fall",
    "falls",
    "lawsuit",
    "probe",
    "risk",
    "weak",
    "loss",
    "cut",
}
POLICY_WORDS = {"regulation", "policy", "tariff", "ban", "approval", "sec", "fed"}
RESEARCH_WORDS = {"analyst", "rating", "target", "broker", "research", "upgrade", "downgrade"}


def _published_at(item: dict) -> str | None:
    ts = item.get("providerPublishTime")
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
    except Exception:
        return None


def _classify(title: str) -> tuple[str, list[str]]:
    words = set(title.lower().replace("-", " ").split())
    labels = []
    score = 0
    if words & POSITIVE_WORDS:
        labels.append("positive")
        score += 1
    if words & NEGATIVE_WORDS:
        labels.append("negative")
        score -= 1
    if words & POLICY_WORDS:
        labels.append("policy")
    if words & RESEARCH_WORDS:
        labels.append("research")
    if not labels:
        labels.append("neutral")
    sentiment = "positive" if score > 0 else "negative" if score < 0 else "neutral"
    return sentiment, labels


def get_news_analysis(ticker: str, as_of_date: str | None = None) -> dict:
    """Fetch recent yfinance news and produce a simple sentiment summary."""

    normalized = ticker.upper()
    try:
        import yfinance as yf

        raw_items = yf.Ticker(normalized).news or []
        items = []
        positive_items = []
        negative_items = []
        policy_items = []
        broker_research_items = []
        score = 0

        for raw in raw_items[:12]:
            title = raw.get("title") or ""
            if not title:
                continue
            sentiment, labels = _classify(title)
            if sentiment == "positive":
                score += 1
            elif sentiment == "negative":
                score -= 1

            item = {
                "title": title,
                "publisher": raw.get("publisher"),
                "link": raw.get("link"),
                "published_at": _published_at(raw),
                "sentiment": sentiment,
                "labels": labels,
            }
            items.append(item)
            if "positive" in labels:
                positive_items.append(item)
            if "negative" in labels:
                negative_items.append(item)
            if "policy" in labels:
                policy_items.append(item)
            if "research" in labels:
                broker_research_items.append(item)

        if not items:
            raise ValueError("empty news result")

        sentiment_score = score / max(len(items), 1)
        if sentiment_score > 0.15:
            summary = "近期新闻情绪偏正面。"
        elif sentiment_score < -0.15:
            summary = "近期新闻情绪偏负面。"
        else:
            summary = "近期新闻情绪整体中性。"

        return {
            "ticker": normalized,
            "as_of_date": as_of_date,
            "items": items,
            "positive_items": positive_items,
            "negative_items": negative_items,
            "policy_items": policy_items,
            "broker_research_items": broker_research_items,
            "sentiment_score": sentiment_score,
            "summary": summary,
            "warnings": [],
            "sources": [{"type": "news", "name": "yfinance"}],
        }
    except Exception as exc:
        return {
            "ticker": normalized,
            "as_of_date": as_of_date,
            "items": [],
            "positive_items": [],
            "negative_items": [],
            "policy_items": [],
            "broker_research_items": [],
            "sentiment_score": 0,
            "summary": "新闻工具暂不可用，当前使用离线降级结果。",
            "warnings": [f"新闻数据获取失败: {exc}"],
            "sources": [{"type": "fallback", "name": "news_analysis_unavailable"}],
        }
