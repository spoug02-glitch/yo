from datetime import datetime, timedelta, timezone

from blog_agent import scoring, config
from blog_agent.news_feeds import NewsItem

NOW = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)


def _item(hours_ago, points=0):
    return NewsItem(id="x", title="t", url="u", source="s",
                    published_utc=NOW - timedelta(hours=hours_ago), points=points)


def test_freshness_full_when_just_published():
    assert scoring.freshness_score(NOW, NOW, 72) == 100.0


def test_freshness_zero_at_cutoff():
    assert scoring.freshness_score(NOW - timedelta(hours=72), NOW, 72) == 0.0


def test_freshness_none_is_zero():
    assert scoring.freshness_score(None, NOW, 72) == 0.0


def test_buzz_saturates():
    assert scoring.buzz_score(8, 8) == 100.0
    assert scoring.buzz_score(16, 8) == 100.0
    assert scoring.buzz_score(4, 8) == 50.0


def test_score_news_cluster_blends():
    cfg = config.load_config()
    # 방금 올라온 글 4개 → freshness 100, buzz 50 → 0.5*100 + 0.5*50 = 75
    cluster = [_item(0) for _ in range(4)]
    assert scoring.score_news_cluster(cluster, NOW, cfg) == 75.0


def test_trend_score_saturates_at_volume_ceiling():
    assert scoring.trend_score(100_000, 100_000) == 100.0
    assert scoring.trend_score(200_000, 100_000) == 100.0
    assert scoring.trend_score(25_000, 100_000) == 25.0


def test_select_topic_picks_highest_above_floor():
    c1 = scoring.Candidate(kind="cert", topic="AICE", longtail="AICE 기초", score=83.0, payload={})
    c2 = scoring.Candidate(kind="news", topic="OpenAI", longtail="OpenAI 신모델", score=90.0, payload={})
    assert scoring.select_topic([c1, c2], floor=60).topic == "OpenAI"


def test_select_topic_returns_none_below_floor():
    c1 = scoring.Candidate(kind="cert", topic="AICE", longtail="x", score=40.0, payload={})
    assert scoring.select_topic([c1], floor=60) is None
