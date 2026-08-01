from blog_agent import charts


def test_table_returns_none(tmp_path):
    spec = {"id": "t1", "type": "table", "title": "x", "data": {}}
    assert charts.render_chart(spec, tmp_path) is None


def test_bar_creates_nonempty_png(tmp_path):
    spec = {"id": "grades", "type": "bar", "title": "응시료",
            "data": {"labels": ["Basic", "Associate"], "values": [50000, 80000]}}
    out = charts.render_chart(spec, tmp_path)
    assert out.exists() and out.suffix == ".png" and out.stat().st_size > 0


def test_donut_creates_nonempty_png(tmp_path):
    spec = {"id": "scope", "type": "donut", "title": "배점",
            "data": {"labels": ["분석", "전처리", "모델링"], "values": [30, 30, 40]}}
    out = charts.render_chart(spec, tmp_path)
    assert out.exists() and out.stat().st_size > 0


def test_flowchart_creates_nonempty_png(tmp_path):
    spec = {"id": "ladder", "type": "flowchart", "title": "등급 사다리",
            "data": {"nodes": ["Basic", "Associate", "Professional"],
                     "edges": [["Basic", "Associate"], ["Associate", "Professional"]]}}
    out = charts.render_chart(spec, tmp_path)
    assert out.exists() and out.stat().st_size > 0


def test_korean_font_picks_installed_family():
    charts.set_korean_font()
    import matplotlib.font_manager as fm
    import matplotlib.pyplot as plt
    installed = {f.name for f in fm.fontManager.ttflist}
    fam = plt.rcParams["font.family"]
    fam_name = fam[0] if isinstance(fam, list) else fam
    assert fam_name in installed


def test_flowchart_with_branching_edges(tmp_path):
    spec = {"id": "branch", "type": "flowchart", "title": "분기",
            "data": {"nodes": ["A", "B", "C"], "edges": [["A", "B"], ["A", "C"]]}}
    out = charts.render_chart(spec, tmp_path)
    assert out.exists() and out.stat().st_size > 0
