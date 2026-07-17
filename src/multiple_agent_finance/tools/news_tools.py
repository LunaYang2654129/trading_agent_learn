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


def _content(item: dict) -> dict:
    content = item.get("content")
    return content if isinstance(content, dict) else item


def _nested_url(value: object) -> str | None:
    if isinstance(value, dict):
        url = value.get("url")
        return str(url) if url else None
    return str(value) if value else None


def _published_at(item: dict) -> str | None:
    content = _content(item)
    pub_date = content.get("pubDate")
    if pub_date:
        return str(pub_date)

    ts = content.get("providerPublishTime")
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


def _fetch_yfinance_news(yf: object, ticker: str) -> list[dict]:
    raw_items = getattr(yf.Ticker(ticker), "news", None) or []
    if raw_items:
        return raw_items

    search = yf.Search(ticker, news_count=12)
    return getattr(search, "news", None) or []


def _summarize_items(items: list[dict]) -> dict:
    positive_items = []
    negative_items = []
    policy_items = []
    broker_research_items = []
    score = 0

    for item in items:
        labels = item.get("labels", [])
        sentiment = item.get("sentiment")
        if sentiment == "positive":
            score += 1
        elif sentiment == "negative":
            score -= 1
        if "positive" in labels:
            positive_items.append(item)
        if "negative" in labels:
            negative_items.append(item)
        if "policy" in labels:
            policy_items.append(item)
        if "research" in labels:
            broker_research_items.append(item)

    sentiment_score = score / max(len(items), 1)
    if sentiment_score > 0.15:
        summary = "近期新闻情绪偏正面。"
    elif sentiment_score < -0.15:
        summary = "近期新闻情绪偏负面。"
    else:
        summary = "近期新闻情绪整体中性。"

    return {
        "positive_items": positive_items,
        "negative_items": negative_items,
        "policy_items": policy_items,
        "broker_research_items": broker_research_items,
        "sentiment_score": sentiment_score,
        "summary": summary,
    }


def _from_local_daily_news(ticker: str, as_of_date: str | None, local_news: dict) -> dict:
    items = []
    for raw in local_news.get("items", []):
        title = raw.get("title") or ""
        if not title:
            continue
        sentiment, labels = _classify(title)
        items.append(
            {
                "title": title,
                "publisher": raw.get("publisher"),
                "link": raw.get("link"),
                "published_at": raw.get("published_at"),
                "news_date": raw.get("news_date"),
                "rank_no": raw.get("rank_no"),
                "sentiment": sentiment,
                "labels": labels,
            }
        )

    if not items:
        raise ValueError("empty local daily news result")

    summary = _summarize_items(items)
    return {
        "ticker": ticker,
        "as_of_date": as_of_date,
        "items": items,
        **summary,
        "coverage": local_news.get("coverage", {}),
        "warnings": [],
        "sources": local_news.get("sources", [{"type": "news_daily_top_items", "name": "local_mysql"}]),
    }


def get_news_analysis(ticker: str, as_of_date: str | None = None) -> dict:
    """Fetch recent yfinance news and produce a simple sentiment summary."""

    normalized = ticker.upper()
    try:
        from multiple_agent_finance.tools.local_data_tools import load_daily_top_news

        local_news = load_daily_top_news(normalized, as_of_date)
        if local_news:
            return _from_local_daily_news(normalized, as_of_date, local_news)
    except Exception as exc:
        local_warning = f"Local daily news unavailable: {exc}"
    else:
        local_warning = "Local daily news not found."

    try:
        import yfinance as yf

        raw_items = _fetch_yfinance_news(yf, normalized)
        items = []

        for raw in raw_items[:12]:
            content = _content(raw)
            title = content.get("title") or ""
            if not title:
                continue
            sentiment, labels = _classify(title)

            item = {
                "title": title,
                "publisher": raw.get("publisher")
                or (content.get("provider") or {}).get("displayName"),
                "link": raw.get("link")
                or _nested_url(content.get("canonicalUrl"))
                or _nested_url(content.get("clickThroughUrl")),
                "published_at": _published_at(raw),
                "sentiment": sentiment,
                "labels": labels,
            }
            items.append(item)

        if not items:
            raise ValueError("empty news result")

        summary = _summarize_items(items)

        return {
            "ticker": normalized,
            "as_of_date": as_of_date,
            "items": items,
            **summary,
            "coverage": {},
            "warnings": [local_warning],
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
            "coverage": {},
            "warnings": [local_warning, f"新闻数据获取失败: {exc}"],
            "sources": [{"type": "fallback", "name": "news_analysis_unavailable"}],
        }
