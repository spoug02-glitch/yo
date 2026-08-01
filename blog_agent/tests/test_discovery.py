import json
from datetime import datetime, timezone

from blog_agent import discovery, config
from blog_agent.news_feeds import NewsItem
from blog_agent.ledger import JsonLedgerStore

NOW = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)


def _news(title, pts=100):
    return NewsItem(id=title, title=title, url="u", source="hackernews",
                    published_utc=NOW, points=pts)


def test_build_candidates_merges_cert_and_news():
    cfg = config.load_config()
    cert = [("AICE", "AICE 기초 가이드", 83.0)]
    news = [_news("OpenAI releases model"), _news("OpenAI releases model 2")]
    cands = discovery.build_candidates(cert_scores=cert, news_items=news, now=NOW, cfg=cfg)
    kinds = {c.kind for c in cands}
    assert kinds == {"cert", "news"}
    cert_c = next(c for c in cands if c.kind == "cert")
    assert cert_c.score == 83.0


def test_build_candidates_includes_trend_scores():
    cfg = config.load_config()
    trend = [("강릉 여행", "강릉 여행", 72.0)]
    cands = discovery.build_candidates(cert_scores=[], news_items=[], now=NOW, cfg=cfg,
                                       trend_scores=trend)
    trend_c = next(c for c in cands if c.kind == "trend")
    assert trend_c.topic == "강릉 여행"
    assert trend_c.score == 72.0


def test_filter_by_ledger_drops_blocked(tmp_path):
    cfg = config.load_config()
    store = JsonLedgerStore(tmp_path / "l.json")
    store.record("cert", "AICE", "AICE 기초 가이드", NOW)
    cands = [discovery.scoring.Candidate(kind="cert", topic="AICE",
             longtail="AICE 기초 가이드", score=83.0, payload={})]
    kept = discovery.filter_by_ledger(cands, store, NOW, cooldown_days=60)
    assert kept == []


def test_news_candidate_payload_is_json_serializable():
    cfg = config.load_config()
    news = [_news("OpenAI releases model"), _news("OpenAI releases model 2")]
    cands = discovery.build_candidates(cert_scores=[], news_items=news, now=NOW, cfg=cfg)
    news_c = next(c for c in cands if c.kind == "news")
    dumped = json.dumps(news_c.payload)
    assert isinstance(dumped, str)
    # published_utc round-trips as an ISO string, not a datetime object
    assert news_c.payload["items"][0]["published_utc"] == NOW.isoformat()


def test_news_candidate_payload_handles_none_published_utc():
    cfg = config.load_config()
    item = NewsItem(id="x", title="No date item", url="u", source="hackernews",
                    published_utc=None, points=10)
    cands = discovery.build_candidates(cert_scores=[], news_items=[item], now=NOW, cfg=cfg)
    news_c = next(c for c in cands if c.kind == "news")
    json.dumps(news_c.payload)  # must not raise
    assert news_c.payload["items"][0]["published_utc"] is None


def test_cluster_news_show_hn_titles_land_in_different_clusters():
    items = [_news("Show HN: my project"), _news("Show HN: rust db")]
    groups = discovery.cluster_news(items)
    assert len(groups) == 2
    keys = set(groups.keys())
    assert "show" not in keys


def test_trend_scores_from_keywords_sums_pc_and_mobile_volume():
    cfg = config.load_config()  # trend.volume_saturation = 100000

    def fake_get_volume(batch):
        return [{"relKeyword": "강릉여행", "monthlyPcQcCnt": 30000, "monthlyMobileQcCnt": 20000}]

    results = discovery.trend_scores_from_keywords(fake_get_volume, ["강릉 여행"], cfg)
    assert results == [("강릉 여행", "강릉 여행", 50.0)]  # (30000+20000)/100000*100


def test_trend_scores_from_keywords_treats_non_int_volume_as_zero():
    # Naver API returns "<10" (a string) for very low-volume keywords, not an int
    cfg = config.load_config()

    def fake_get_volume(batch):
        return [{"relKeyword": "희귀키워드", "monthlyPcQcCnt": "<10", "monthlyMobileQcCnt": "<10"}]

    results = discovery.trend_scores_from_keywords(fake_get_volume, ["희귀키워드"], cfg)
    assert results == [("희귀키워드", "희귀키워드", 0.0)]


def test_trend_scores_from_keywords_strips_commas_before_batching():
    # 실검 문구에 쉼표가 섞이면("최태원, 하이닉스 주가 매수") kiwi의 콤마-구분 배치
    # 프로토콜과 충돌해 그 배치 전체가 빈 응답으로 온다(2026-07-31 실행에서 실제 발생).
    # 보낼 때 이미 쉼표가 제거된 상태여야 한다.
    cfg = config.load_config()
    sent_batches = []

    def fake_get_volume(batch):
        sent_batches.append(list(batch))
        return [{"relKeyword": "최태원하이닉스주가매수", "monthlyPcQcCnt": 5000, "monthlyMobileQcCnt": 5000}]

    results = discovery.trend_scores_from_keywords(
        fake_get_volume, ["최태원, 하이닉스 주가 매수"], cfg)
    assert sent_batches == [["최태원하이닉스주가매수"]]  # comma AND space stripped before sending
    assert results == [("최태원, 하이닉스 주가 매수", "최태원, 하이닉스 주가 매수", 10.0)]


def test_trend_scores_from_keywords_comma_keyword_does_not_split_batch_size():
    # 5개 배치 안에 쉼표 포함 키워드가 있어도 실제 전송 배치 크기는 여전히 5여야 한다
    # (쉼표 미제거 시 join 결과가 6토큰으로 쪼개지던 버그의 회귀 테스트).
    cfg = config.load_config()
    sent_batches = []

    def fake_get_volume(batch):
        sent_batches.append(list(batch))
        return []

    keywords = ["최태원, 하이닉스 주가 매수", "미래에셋증권", "달러", "해고", "송강호"]
    discovery.trend_scores_from_keywords(fake_get_volume, keywords, cfg)
    assert len(sent_batches) == 1
    assert len(sent_batches[0]) == 5
    assert all("," not in kw for kw in sent_batches[0])


def test_trend_scores_from_keywords_skips_batch_failure_and_missing_match():
    cfg = config.load_config()
    calls = []

    def fake_get_volume(batch):
        calls.append(list(batch))
        if "실패키워드" in batch:
            raise RuntimeError("upstream failure")
        return [{"relKeyword": "정상키워드", "monthlyPcQcCnt": 1000, "monthlyMobileQcCnt": 0}]

    # 6 keywords forces 2 batches (batch size 5); one keyword has no matching row back
    keywords = ["정상키워드", "빠진키워드", "a", "b", "c", "실패키워드"]
    results = discovery.trend_scores_from_keywords(fake_get_volume, keywords, cfg)
    assert results == [("정상키워드", "정상키워드", 1.0)]
    assert len(calls) == 2  # batched into two calls of size 5 and 1


def test_cert_scores_from_kiwi_skips_failures_and_missing_score():
    def fake_analyze(kw):
        if kw == "AICE":
            return {"composite_score": 83.9}
        if kw == "빅데이터분석기사":
            raise RuntimeError("upstream failure")
        return {}

    seeds = ["AICE", "빅데이터분석기사", "ADsP"]
    results = discovery.cert_scores_from_kiwi(fake_analyze, seeds)
    assert results == [("AICE", "AICE", 83.9)]
