"""오늘의 실시간 화제 키워드 (signal.bz) — 로그인/브라우저 불필요, 순수 HTTP.

크리에이터 어드바이저(네이버 자체, 로그인 필요, 어제 데이터)의 대체 소스로 채택.
signal.bz는 여러 포털의 실시간 검색어 신호를 집계하는 공개 API(api.signal.bz)를
제공하며, 이 함수는 그 top10 키워드만 뽑아 discovery.trend_scores_from_keywords에
넘길 순수 키워드 리스트로 반환한다. 실제 채택 여부(검색량 높은 주제인가)는 여기서
판단하지 않는다 — kiwi 검색광고 API로 검증하는 건 trend_scores_from_keywords의 몫이다.
"""
from __future__ import annotations

import requests

_URL = "https://api.signal.bz/news/realtime"


def fetch_trending_keywords(*, http=requests) -> list[str]:
    """실패하면 빈 리스트 — 이 소스 하나가 죽어도 발굴 전체가 죽지 않게 한다.

    네트워크/JSON 파싱 실패뿐 아니라, API 응답 **구조가 달라지는 경우**(top10이 리스트가
    아니게 바뀜, 항목이 dict가 아님, rank/keyword 필드명이 바뀜 등)도 전부 이 함수 안에서
    흡수한다 — 외부 서비스가 스키마를 바꿔도 호출자(발굴 파이프라인 전체)가 죽지 않게.
    """
    try:
        resp = http.get(_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        resp.raise_for_status()
        data = resp.json()  # response.json()은 인코딩 선언과 무관하게 UTF-8로 정확히 디코드한다
        rows = data.get("top10", [])
        if not isinstance(rows, list):
            return []
        valid = [r for r in rows if isinstance(r, dict) and r.get("keyword")]
        return [r["keyword"] for r in sorted(valid, key=lambda r: r.get("rank", 999))]
    except Exception:
        return []
