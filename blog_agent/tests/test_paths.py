from blog_agent import paths

_ILLEGAL = set('<>:"/\\|?*')


def test_output_docx_strips_illegal_windows_chars():
    out = paths.output_docx("2026-07-29", 'Show HN: a? b<c>|d*')
    name = out.name
    assert name.endswith(".docx")
    assert _ILLEGAL.isdisjoint(set(name))


def test_output_docx_strips_trailing_dots_and_spaces():
    out = paths.output_docx("2026-07-29", "Some Topic.   ")
    stem = out.name[: -len(".docx")]
    assert not stem.endswith(".")
    assert not stem.endswith(" ")
    assert stem == "2026-07-29_Some Topic"


def test_output_docx_caps_topic_at_80_chars():
    long_topic = "A" * 200
    out = paths.output_docx("2026-07-29", long_topic)
    stem = out.name[: -len(".docx")]
    topic_part = stem[len("2026-07-29_"):]
    assert len(topic_part) <= 80


def test_work_dir_creates_directory_under_blog(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "_BLOG_ROOT", tmp_path / "Blog")
    d = paths.work_dir("2026-07-29")
    assert d.exists()
    assert d.is_dir()
    assert d == tmp_path / "Blog" / ".work" / "2026-07-29"


def test_runlog_creates_directory_under_blog(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "_BLOG_ROOT", tmp_path / "Blog")
    p = paths.runlog("2026-07-29")
    assert p.parent.exists()
    assert p.parent.is_dir()
    assert p == tmp_path / "Blog" / ".runlog" / "2026-07-29.json"


def test_work_dir_with_slug_isolates_same_day_runs(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "_BLOG_ROOT", tmp_path / "Blog")
    run1 = paths.work_dir("2026-07-29", slug="빅데이터분석기사")
    run2 = paths.work_dir("2026-07-29", slug="강릉 여행")
    assert run1 != run2
    assert run1.exists() and run2.exists()
    assert run1.parent == run2.parent == tmp_path / "Blog" / ".work" / "2026-07-29"


def test_runlog_with_slug_isolates_same_day_runs(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "_BLOG_ROOT", tmp_path / "Blog")
    run1 = paths.runlog("2026-07-29", slug="빅데이터분석기사")
    run2 = paths.runlog("2026-07-29", slug="강릉 여행")
    assert run1 != run2
    assert run1.name.startswith("2026-07-29-")
    assert run1.parent == run2.parent == tmp_path / "Blog" / ".runlog"
