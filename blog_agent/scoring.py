from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from . import config
from .news_feeds import NewsItem


@dataclass(frozen=True)
class Candidate:
    kind: str          # "cert" | "news" | "trend"
    topic: str
    longtail: str
    score: float
    payload: dict


def freshness_score(published_utc: datetime | None, now: datetime, zero_hours: float) -> float:
    if published_utc is None:
        return 0.0
    hours = (now - published_utc).total_seconds() / 3600.0
    if hours <= 0:
        return 100.0
    if hours >= zero_hours:
        return 0.0
    return round((1.0 - hours / zero_hours) * 100.0, 4)


def buzz_score(count: int, saturation: int) -> float:
    if count >= saturation:
        return 100.0
    return round(count / saturation * 100.0, 4)


def score_news_cluster(items: list[NewsItem], now: datetime, cfg: dict) -> float:
    zero_hours = config.value(cfg, "news.freshness_zero_hours")
    saturation = config.value(cfg, "news.buzz_saturation_count")
    wf = config.value(cfg, "news.weight_freshness")
    wb = config.value(cfg, "news.weight_buzz")
    freshest = max((i.published_utc for i in items if i.published_utc), default=None)
    fresh = freshness_score(freshest, now, zero_hours)
    buzz = buzz_score(len(items), saturation)
    return round(wf * fresh + wb * buzz, 4)


def trend_score(monthly_volume: int, saturation: int) -> float:
    """검색량만 반영하는 점수 — 경쟁도 계산 없이 '무조건 검색량 높은 주제' 우선."""
    if monthly_volume >= saturation:
        return 100.0
    return round(monthly_volume / saturation * 100.0, 4)


def select_topic(candidates: list[Candidate], floor: float) -> Candidate | None:
    eligible = [c for c in candidates if c.score >= floor]
    if not eligible:
        return None
    return max(eligible, key=lambda c: c.score)
