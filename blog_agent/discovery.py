from __future__ import annotations

import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from typing import Callable

from . import config, scoring
from .news_feeds import NewsItem
from .ledger import LedgerStore
from .scoring import Candidate

_VOLUME_BATCH_SIZE = 5  # kiwi get_keyword_volume caps hintKeywords at 5 per call

_STOP = {"the", "a", "an", "to", "of", "for", "and", "releases", "release", "new",
        "show", "ask", "hn", "tell"}


def _topic_key(title: str) -> str:
    toks = [t for t in re.findall(r"[A-Za-z0-9가-힣]+", title.lower()) if t not in _STOP]
    return toks[0] if toks else title.lower()


def cluster_news(items: list[NewsItem]) -> dict[str, list[NewsItem]]:
    groups: dict[str, list[NewsItem]] = defaultdict(list)
    for it in items:
        groups[_topic_key(it.title)].append(it)
    return dict(groups)


def _news_item_json(i: NewsItem) -> dict:
    return {**i.__dict__, "published_utc": i.published_utc.isoformat() if i.published_utc else None}


def build_candidates(*, cert_scores: list[tuple[str, str, float]],
                     news_items: list[NewsItem], now: datetime, cfg: dict,
                     trend_scores: list[tuple[str, str, float]] = ()) -> list[Candidate]:
    cands: list[Candidate] = []
    for topic, longtail, score in cert_scores:
        cands.append(Candidate(kind="cert", topic=topic, longtail=longtail,
                               score=float(score), payload={}))
    for topic, longtail, score in trend_scores:
        cands.append(Candidate(kind="trend", topic=topic, longtail=longtail,
                               score=float(score), payload={}))
    for key, group in cluster_news(news_items).items():
        rep = max(group, key=lambda i: i.points)
        cands.append(Candidate(
            kind="news", topic=rep.title, longtail=rep.title,
            score=scoring.score_news_cluster(group, now, cfg),
            payload={"items": [_news_item_json(i) for i in group]},
        ))
    return cands


def filter_by_ledger(cands: list[Candidate], store: LedgerStore,
                     now: datetime, cooldown_days: int) -> list[Candidate]:
    return [c for c in cands if not store.is_blocked(c.longtail, now, cooldown_days)]


def load_kiwi_analyze() -> Callable:
    kiwi_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "kiwi")
    if kiwi_dir not in sys.path:
        sys.path.insert(0, kiwi_dir)
    from blue_ocean_finder import analyze_keyword  # type: ignore
    return analyze_keyword


def _batched(items: list[str], size: int) -> list[list[str]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def _clean_trend_keyword(kw: str) -> str:
    """공백·쉼표 제거 — kiwi get_keyword_volume이 여러 키워드를 ','로 이어붙여
    한 번에 보내므로, 키워드 안에 쉼표가 남아있으면(뉴스 헤드라인식 실검 문구에
    흔함, 예: "최태원, 하이닉스 주가 매수") 배치 구분자와 충돌해 그 배치 전체가
    빈 응답으로 돌아온다(2026-07-31 실행에서 실제로 겪음 — batch 5개가 쉼표 때문에
    6개로 쪼개져 응답 0건). 보내기 전에 미리 제거해 원천 차단한다."""
    return kw.replace(" ", "").replace(",", "")


def is_excluded_trend_topic(keyword: str, cfg: dict) -> bool:
    """정치·연예 카테고리 휴리스틱 필터 (2026-08 사용자 지시).

    정치는 논란 리스크가 커서, 연예는 "데이터로 보는" 앵글로 파낼 게 없어서
    후보에서 제외한다. 부분일치 키워드 목록 기반이라 완벽하지 않음 — 새 정치인·
    셀럽 이름은 못 걸러낼 수 있다(config.json trend.exclude_patterns 참고)."""
    patterns = config.value(cfg, "trend.exclude_patterns")
    return any(p in keyword for p in patterns)


def trend_scores_from_keywords(get_volume_fn, keywords: list[str],
                               cfg: dict) -> list[tuple[str, str, float]]:
    """크리에이터 어드바이저 급상승 키워드 → kiwi 검색광고 월간 검색량만으로 점수화.

    경쟁도(블루오션) 계산 없이 '검색량이 곧 점수'다 — 이 소스의 존재 이유가
    "일단 무조건 검색량이 높은 주제를 잡는다"이기 때문. 실패한 키워드는 건너뛴다.
    정치·연예로 분류되는 키워드는 점수 산정 전에 제외한다(is_excluded_trend_topic).
    """
    keywords = [kw for kw in keywords if not is_excluded_trend_topic(kw, cfg)]
    saturation = config.value(cfg, "trend.volume_saturation")
    results: list[tuple[str, str, float]] = []
    for batch in _batched(keywords, _VOLUME_BATCH_SIZE):
        cleaned_batch = [_clean_trend_keyword(kw) for kw in batch]
        try:
            rows = get_volume_fn(cleaned_batch)  # 정제된 문자열을 보내야 쉼표가 배치를 안 쪼갠다
        except Exception:
            continue
        for kw, cleaned in zip(batch, cleaned_batch):
            match = next((r for r in rows if r.get("relKeyword") == cleaned), None)
            if match is None:
                continue
            pc = match.get("monthlyPcQcCnt", 0)
            mobile = match.get("monthlyMobileQcCnt", 0)
            volume = (pc if isinstance(pc, int) else 0) + (mobile if isinstance(mobile, int) else 0)
            results.append((kw, kw, scoring.trend_score(volume, saturation)))
    return results


def cert_scores_from_kiwi(analyze_fn, seeds: list[str]) -> list[tuple[str, str, float]]:
    """kiwi blue_ocean analyze_keyword dict → (topic, longtail, score). Failures skipped."""
    results: list[tuple[str, str, float]] = []
    for kw in seeds:
        try:
            res = analyze_fn(kw)
        except Exception:
            continue
        score = res.get("composite_score") if isinstance(res, dict) else None
        if score is None:
            continue
        results.append((kw, kw, float(score)))
    return results
