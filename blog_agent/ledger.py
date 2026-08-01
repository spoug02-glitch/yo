from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

_PARTICLES = ["을", "를", "이", "가", "은", "는", "의", "에", "로", "으로"]


def _as_utc(dt: datetime) -> datetime:
    """Normalize a naive or aware datetime to a UTC-aware datetime."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def normalize_longtail(s: str) -> str:
    text = re.sub(r"\s+", "", s.strip().lower())
    # 끝에 붙은 조사 제거(정확일치 정규화용, 근사) — 긴 것부터 매칭
    for p in sorted(_PARTICLES, key=len, reverse=True):
        if text.endswith(p) and len(text) > len(p):
            text = text[: -len(p)]
            break
    return text


class LedgerStore(Protocol):
    def is_blocked(self, longtail: str, now: datetime, cooldown_days: int) -> bool: ...
    def record(self, kind: str, topic: str, longtail: str, now: datetime) -> None: ...


class JsonLedgerStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._rows = self._load()

    def _load(self) -> list[dict]:
        if self.path.exists():
            return json.loads(self.path.read_text(encoding="utf-8"))
        return []

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._rows, ensure_ascii=False, indent=2), encoding="utf-8")

    def is_blocked(self, longtail: str, now: datetime, cooldown_days: int) -> bool:
        norm = normalize_longtail(longtail)
        now_utc = _as_utc(now)
        for row in self._rows:
            if row.get("norm") != norm:
                continue
            used = _as_utc(datetime.fromisoformat(row["date"]))
            if (now_utc - used).days < cooldown_days:
                return True
        return False

    def record(self, kind: str, topic: str, longtail: str, now: datetime) -> None:
        self._rows.append({
            "kind": kind, "topic": topic, "longtail": longtail,
            "norm": normalize_longtail(longtail), "date": _as_utc(now).isoformat(),
        })
        self._save()
