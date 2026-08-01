from pathlib import Path

from PIL import Image

from blog_agent import html_builder


def _png(tmp_path) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    p = tmp_path / "c.png"
    fig, ax = plt.subplots()
    ax.plot([1, 2])
    fig.savefig(p)
    plt.close(fig)
    return p


def test_build_html_embeds_table_image_and_styles(tmp_path):
    body = "# 제목\n\n## 소제목\n\n본문 **강조** 문장.\n\n{{chart:t1}}\n\n{{chart:img1}}\n"
    out = html_builder.build_html(
        body_md=body,
        table_specs={"t1": {"data": {"headers": ["a"], "rows": [["b"]]}}},
        chart_images={"img1": _png(tmp_path)},
        sources=["출처 A — 확인일 2026-07-29"],
        out_path=tmp_path / "out.html")
    text = out.read_text(encoding="utf-8")
    assert "나눔고딕" in text
    assert "font-size:19px" in text          # h2 rule
    assert ('<p style="font-size:15px;"><span style="font-size:15px;">'
            "본문 <strong>강조</strong> 문장.</span></p>") in text
    assert "<table" in text and "<th" in text
    assert "data:image/png;base64," in text  # image embedded, no file refs
    assert "출처 A" in text


def test_wide_image_gets_explicit_html_width_attribute_not_just_style(tmp_path):
    # mimics a screenshotted infographic card (~1900px raw) that must be
    # downscaled via HTML attribute, since paste sanitizers often strip the
    # style="max-width:100%" CSS but keep the width/height attributes.
    p = tmp_path / "wide.png"
    Image.new("RGB", (1400, 700), "white").save(p)
    out = html_builder.build_html(
        body_md="{{chart:wide}}", table_specs={}, chart_images={"wide": p},
        sources=[], out_path=tmp_path / "wide.html")
    assert 'width="700" height="350"' in out.read_text(encoding="utf-8")


def test_small_image_not_upscaled_past_native_width(tmp_path):
    p = tmp_path / "tiny.png"
    Image.new("RGB", (100, 50), "white").save(p)
    out = html_builder.build_html(
        body_md="{{chart:tiny}}", table_specs={}, chart_images={"tiny": p},
        sources=[], out_path=tmp_path / "small.html")
    assert 'width="100" height="50"' in out.read_text(encoding="utf-8")


def test_source_urls_become_clickable_links(tmp_path):
    body = "## 출처\n\n- 데이터자격검정 — https://www.dataq.or.kr/www/sub/a_07.do\n"
    out = html_builder.build_html(
        body_md=body, table_specs={}, chart_images={}, sources=[],
        out_path=tmp_path / "src.html")
    text = out.read_text(encoding="utf-8")
    assert '<a href="https://www.dataq.or.kr/www/sub/a_07.do" target="_blank" rel="noopener">https://www.dataq.or.kr/www/sub/a_07.do</a>' in text


def test_title_candidates_become_hidden_comment(tmp_path):
    out = html_builder.build_html(
        body_md="본문", table_specs={}, chart_images={}, sources=[],
        title_candidates=["제목 A", "제목 B"],
        out_path=tmp_path / "t.html")
    text = out.read_text(encoding="utf-8")
    assert "<!--" in text and "1. 제목 A" in text and "2. 제목 B" in text
    # the comment must close before the visible body div starts
    assert text.index("-->") < text.index('<div style=')


def test_bullet_and_source_text_wrapped_in_size_span(tmp_path):
    body = "- 항목 하나\n"
    out = html_builder.build_html(
        body_md=body, table_specs={}, chart_images={},
        sources=["출처 X"], out_path=tmp_path / "b.html")
    text = out.read_text(encoding="utf-8")
    assert '<li style="font-size:15px;"><span style="font-size:15px;">항목 하나</span></li>' in text
    assert '<span style="font-size:12px;">출처 X</span>' in text


def test_unknown_marker_visible(tmp_path):
    out = html_builder.build_html(
        body_md="{{chart:nope}}", table_specs={}, chart_images={},
        sources=[], out_path=tmp_path / "o.html")
    assert "[도표 누락: nope]" in out.read_text(encoding="utf-8")
