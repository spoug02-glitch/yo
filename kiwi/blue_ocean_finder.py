"""
블루오션 파인더 - "이 키워드로 지금 글을 쓰면 상위 노출될 가능성이 얼마나 높은가"를
데이터 기반으로 점수화한다. 발행량 총량 추정이 목적이 아니라 경쟁 강도 점수화가 목적.

데이터 소스: 네이버 블로그 검색 API(상위 100개, 정확도순) + 데이터랩 검색어트렌드.
가중치는 weights.json에서 읽어온다 (실제 성과를 보면서 조정할 수 있도록 코드에 박아넣지 않음).
"""

import json
import os
import re
from collections import Counter
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

from naver_datalab_trend import get_search_trend

load_dotenv()

CLIENT_ID = os.getenv("NAVER_SEARCH_CLIENT_ID")
CLIENT_SECRET = os.getenv("NAVER_SEARCH_CLIENT_SECRET")

BLOG_SEARCH_URL = "https://openapi.naver.com/v1/search/blog.json"

WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "weights.json")

AD_TERMS = ["체험단", "협찬", "지원받아", "소정의", "원고료", "제공받아"]

TAG_RE = re.compile(r"<[^>]+>")
WORD_RE = re.compile(r"\w+", re.UNICODE)
BLOG_ID_RE = re.compile(r"blog\.naver\.com/([^/?]+)")


def load_weights() -> dict:
    with open(WEIGHTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_top_blogs(keyword: str, display: int = 100) -> list[dict]:
    """정확도순(sim, 기본 정렬) 상위 블로그 글을 가져온다 - 실제 검색결과 순서에 가장 가까움."""
    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET,
    }
    params = {"query": keyword, "display": display, "start": 1}
    response = requests.get(BLOG_SEARCH_URL, headers=headers, params=params)
    if response.status_code != 200:
        raise RuntimeError(f"블로그 검색 API 실패 (status={response.status_code}): {response.text}")
    return response.json().get("items", [])


def _strip_tags(text: str) -> str:
    return TAG_RE.sub("", text or "")


def _jaccard_distance(a: set, b: set) -> float:
    union = a | b
    if not union:
        return 0.0
    return 1 - len(a & b) / len(union)


def _title_diversity_score(titles: list[str]) -> float:
    token_sets = [set(WORD_RE.findall(t)) for t in titles]
    n = len(token_sets)
    if n < 2:
        return 100.0
    total = 0.0
    pairs = 0
    for i in range(n):
        for j in range(i + 1, n):
            total += _jaccard_distance(token_sets[i], token_sets[j])
            pairs += 1
    return round((total / pairs) * 100, 1) if pairs else 100.0


def _extract_blog_id(link: str) -> str | None:
    match = BLOG_ID_RE.search(link or "")
    return match.group(1) if match else None


def _trend_score(keyword: str) -> float:
    """최근 30일 검색량 평균을 그 이전 30일과 비교해 상승세면 높은 점수를 준다."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)

    result = get_search_trend(
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        keyword_groups=[{"groupName": keyword, "keywords": [keyword]}],
        time_unit="date",
    )
    groups = result.get("results", [])
    if not groups:
        return 50.0

    data = groups[0].get("data", [])
    if len(data) < 2:
        return 50.0

    mid = len(data) // 2
    first_half = [p["ratio"] for p in data[:mid]]
    second_half = [p["ratio"] for p in data[mid:]]
    avg1 = sum(first_half) / len(first_half) if first_half else 0
    avg2 = sum(second_half) / len(second_half) if second_half else 0

    if avg1 <= 0:
        return 50.0

    pct_change = (avg2 - avg1) / avg1 * 100
    score = 50 + pct_change / 2
    return round(max(0.0, min(100.0, score)), 1)


def grade_label(score: float) -> str:
    if score >= 80:
        return "🔥 블루오션"
    if score >= 60:
        return "🙂 기회 있음"
    if score >= 40:
        return "⚠️ 보통"
    return "🔴 레드오션"


def stars(score: float, max_score: float = 100.0) -> str:
    filled = max(0, min(5, round(score / max_score * 5)))
    return "★" * filled + "☆" * (5 - filled)


def analyze_keyword(keyword: str, weights: dict | None = None) -> dict:
    items = fetch_top_blogs(keyword, display=100)
    if not items:
        raise RuntimeError("블로그 검색 결과가 없습니다.")

    now = datetime.now()
    dates = [datetime.strptime(it["postdate"], "%Y%m%d") for it in items]
    total = len(items)

    recent7 = sum(1 for d in dates if (now - d).days <= 7)
    recent30 = sum(1 for d in dates if (now - d).days <= 30)
    recent90 = sum(1 for d in dates if (now - d).days <= 90)
    old1y = sum(1 for d in dates if (now - d).days >= 365)
    old6m = sum(1 for d in dates if (now - d).days >= 180)
    old6m_pct = round(old6m / total * 100, 1)
    recent30_pct = round(recent30 / total * 100, 1)
    freshness_score = round(max(0.0, 100 - recent30_pct), 1)

    top10 = items[:10]
    top10_dates = dates[:10]
    top10_authors = [_extract_blog_id(it.get("link", "")) for it in top10]
    unique_top10 = len({a for a in top10_authors if a})
    dominance_score = round(unique_top10 / len(top10) * 100, 1) if top10 else 0.0
    author_counts = Counter(a for a in top10_authors if a)
    max_author_count_top10 = max(author_counts.values()) if author_counts else 0

    titles_clean = [_strip_tags(it.get("title", "")) for it in items]
    diversity_score = _title_diversity_score(titles_clean)

    word_count = len(keyword.split())
    keyword_length_score = min(100.0, word_count * 25.0)

    trend_score = _trend_score(keyword)

    w = weights or load_weights()
    composite = round(
        w["freshness"] * freshness_score
        + w["dominance"] * dominance_score
        + w["diversity"] * diversity_score
        + w["keyword_length"] * keyword_length_score
        + w["trend"] * trend_score,
        1,
    )

    new_entrant_count = sum(1 for d in top10_dates if (now - d).days <= 30)
    avg_age_days = round(sum((now - d).days for d in top10_dates) / len(top10_dates)) if top10_dates else None

    ad_count = sum(
        1
        for it in items
        if any(term in (_strip_tags(it.get("title", "")) + _strip_tags(it.get("description", ""))) for term in AD_TERMS)
    )
    ad_pct = round(ad_count / total * 100, 1)

    return {
        "keyword": keyword,
        "total_collected": total,
        "freshness_score": freshness_score,
        "recent7_count": recent7,
        "recent30_count": recent30,
        "recent90_count": recent90,
        "recent30_pct": recent30_pct,
        "old1y_count": old1y,
        "old6m_pct": old6m_pct,
        "dominance_score": dominance_score,
        "unique_top10_authors": unique_top10,
        "max_author_count_top10": max_author_count_top10,
        "diversity_score": diversity_score,
        "keyword_length_score": keyword_length_score,
        "word_count": word_count,
        "trend_score": trend_score,
        "composite_score": composite,
        "grade": grade_label(composite),
        "new_entrant_count": new_entrant_count,
        "avg_age_days": avg_age_days,
        "ad_pct": ad_pct,
        "ad_count": ad_count,
    }
