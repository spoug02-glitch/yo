from pathlib import Path

# blog_agent/ 의 부모(레포 루트)/Blog
_BLOG_ROOT = Path(__file__).resolve().parent.parent / "Blog"

_ILLEGAL_CHARS = set('<>:"/\\|?*')
_MAX_TOPIC_LEN = 80


def _sanitize_topic(topic: str) -> str:
    chars = [
        "_" if (ch in _ILLEGAL_CHARS or ord(ch) < 32) else ch
        for ch in topic
    ]
    safe = "".join(chars).rstrip(" .")
    return safe[:_MAX_TOPIC_LEN].rstrip(" .")


def work_dir(date_str: str, slug: str | None = None) -> Path:
    """slug 없으면 날짜 폴더 자체(하위호환). slug 있으면 그 아래 topic별 하위폴더 —
    하루 2회(이상) 실행 시 각 실행의 research.md/draft.md/charts 등이 서로 덮어쓰지 않게 격리한다."""
    p = _BLOG_ROOT / ".work" / date_str
    if slug is not None:
        p = p / _sanitize_topic(slug)
    p.mkdir(parents=True, exist_ok=True)
    return p


def output_docx(date_str: str, topic: str) -> Path:
    safe = _sanitize_topic(topic)
    return _BLOG_ROOT / f"{date_str}_{safe}.docx"


def runlog(date_str: str, slug: str | None = None) -> Path:
    """slug 없으면 날짜별 파일(하위호환). slug 있으면 실행별 파일 —
    하루 2회 실행 시 1회차 실행기록을 2회차가 덮어쓰지 않게 한다."""
    p = _BLOG_ROOT / ".runlog"
    p.mkdir(parents=True, exist_ok=True)
    name = f"{date_str}.json" if slug is None else f"{date_str}-{_sanitize_topic(slug)}.json"
    return p / name
