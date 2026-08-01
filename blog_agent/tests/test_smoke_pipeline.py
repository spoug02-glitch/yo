from datetime import datetime, timezone

from blog_agent import config, discovery, scoring, charts, docx_builder
from blog_agent.news_feeds import NewsItem
from blog_agent.ledger import JsonLedgerStore

NOW = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)


def test_core_pipeline_produces_docx(tmp_path):
    cfg = config.load_config()
    # 발굴(주입 데이터)
    cert = [("AICE", "AICE 처음 시작 가이드", 83.9)]
    news = [NewsItem(id=f"n{i}", title="OpenAI new model", url="u",
                     source="hackernews", published_utc=NOW, points=200) for i in range(3)]
    cands = discovery.build_candidates(cert_scores=cert, news_items=news, now=NOW, cfg=cfg)

    # 원장 필터 + 선택
    store = JsonLedgerStore(tmp_path / "ledger.json")
    cands = discovery.filter_by_ledger(cands, store, NOW,
                                       cooldown_days=config.value(cfg, "ledger.cooldown_days"))
    chosen = scoring.select_topic(cands, floor=config.value(cfg, "score_floor"))
    assert chosen is not None

    # 차트 렌더
    spec = {"id": "fees", "type": "bar", "title": "응시료",
            "data": {"labels": ["Basic", "Associate"], "values": [50000, 80000]}}
    png = charts.render_chart(spec, tmp_path)

    # 조립
    body = "# 가이드\n\n## 1. 개요\n\n본문.\n\n{{chart:fees}}\n"
    out = docx_builder.build_docx(
        title_candidates=["후보1", "후보2", "후보3", "후보4", "후보5"],
        body_md=body, table_specs={}, chart_images={"fees": png},
        sources=["공식 aice.study — 확인일 2026-07-29"], out_path=tmp_path / "final.docx")
    assert out.exists() and out.stat().st_size > 0

    # 원장 기록 후 재차단 확인
    store.record(chosen.kind, chosen.topic, chosen.longtail, NOW)
    assert store.is_blocked(chosen.longtail, NOW, 60) is True
