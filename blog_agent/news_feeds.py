from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import requests
import feedparser

from . import config

_HN_BASE = "https://hacker-news.firebaseio.com/v0"


@dataclass(frozen=True)
class NewsItem:
    id: str
    title: str
    url: str
    source: str
    published_utc: datetime | None
    points: int


def fetch_hackernews(top_n: int = 30, *, http=requests, now: datetime | None = None) -> list[NewsItem]:
    ids = http.get(f"{_HN_BASE}/topstories.json", timeout=10).json()[:top_n]
    items: list[NewsItem] = []
    for sid in ids:
        data = http.get(f"{_HN_BASE}/item/{sid}.json", timeout=10).json()
        if not data or data.get("type") != "story" or not data.get("title"):
            continue
        ts = data.get("time")
        pub = datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None
        items.append(NewsItem(
            id=str(data["id"]),
            title=data["title"],
            url=data.get("url") or f"https://news.ycombinator.com/item?id={data['id']}",
            source="hackernews",
            published_utc=pub,
            points=int(data.get("score", 0)),
        ))
    return items


def _rss_dt(entry) -> datetime | None:
    tm = getattr(entry, "published_parsed", None)
    if not tm:
        return None
    return datetime(*tm[:6], tzinfo=timezone.utc)


def fetch_rss(feed_urls: list[str], *, parse=feedparser.parse) -> list[NewsItem]:
    items: list[NewsItem] = []
    for url in feed_urls:
        feed = parse(url)
        for e in feed.entries:
            items.append(NewsItem(
                id=getattr(e, "link", getattr(e, "title", "")),
                title=getattr(e, "title", ""),
                url=getattr(e, "link", ""),
                source=url,
                published_utc=_rss_dt(e),
                points=0,
            ))
    return items


def gather_news(cfg: dict, *, http=requests, parse=feedparser.parse) -> tuple[list[NewsItem], list[str]]:
    """소스별 격리 수집: 한 소스가 죽어도 나머지는 살린다. 실패 목록을 함께 반환."""
    items: list[NewsItem] = []
    failures: list[str] = []
    try:
        items += fetch_hackernews(http=http)
    except Exception as e:
        failures.append(f"hackernews: {e}")
    for url in config.value(cfg, "rss_feeds"):
        try:
            items += fetch_rss([url], parse=parse)
        except Exception as e:
            failures.append(f"rss {url}: {e}")
    return items, failures
