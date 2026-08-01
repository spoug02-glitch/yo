"""Markdown draft → publish-ready HTML (blog-post-writer skill §3-6 formatting).

Charts: table specs render as native <table>; png charts embed as base64 data
URIs so the single .html file is self-contained — open in a browser, select
all, copy, paste into the Naver/Tistory editor and formatting + images carry
over (which pasting from Word does not).
"""
from __future__ import annotations

import base64
import html
import re
from pathlib import Path

from PIL import Image

# Naver's paste sanitizer drops the <img style="max-width:100%"> CSS, so a
# raw ~1900px screenshot pastes at native resolution and blows out past the
# blog's content column (the excess gets clipped, not scaled). An explicit
# `width` HTML ATTRIBUTE survives paste far more reliably than style, and
# per standard img sizing rules a width-only attribute still scales height
# proportionally. 700px is a safe fit for common Korean blog content columns.
_IMG_DISPLAY_WIDTH = 700

_CHART_RE = re.compile(r"^\{\{chart:(?P<id>[^}]+)\}\}$")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"\*([^*]+)\*")
_URL_RE = re.compile(r"https?://[^\s<>\"']+")


# Sizes use px, not pt. Naver's toolbar size dropdown is *labeled* "pt" but
# the underlying CSS it applies is px (a common Korean-CMS UI mislabel) --
# pasted `font-size:15pt` renders at ~20px and gets snapped to the nearest
# preset (19), which is exactly the drift observed (본문 15pt -> 19 shown
# in the toolbar after paste). Using `15px` etc. matches the preset exactly.
_STYLE = (
    "font-family:'나눔고딕','NanumGothic',sans-serif;"
    "font-size:15px;line-height:1.7;max-width:52em;margin:0 auto;padding:1em;"
)
_H1 = "font-size:24px;font-weight:700;"
_H2 = "font-size:19px;font-weight:700;margin-top:1.6em;"
_H3 = "font-size:15px;font-style:italic;font-weight:400;margin-top:1.2em;"
_TABLE = "border-collapse:collapse;margin:1em 0;"
_CELL = "border:1px solid #999;padding:6px 10px;font-size:15px;"


def _linkify(escaped_text: str) -> str:
    """Turn bare URLs in already-escaped text into clickable anchors.

    Runs on html.escape()'d text, so URLs never contain literal '<', '>', '"'
    (those are escaped to entities) and the regex-matched span is safe to
    wrap without re-escaping.
    """
    return _URL_RE.sub(lambda m: f'<a href="{m.group(0)}" target="_blank" rel="noopener">{m.group(0)}</a>',
                       escaped_text)


def _inline(text: str) -> str:
    out = html.escape(text)
    out = _BOLD_RE.sub(r"<strong>\1</strong>", out)
    out = _ITALIC_RE.sub(r"<em>\1</em>", out)
    out = _linkify(out)
    return out


def _run(text: str, size_px: int) -> str:
    """Inline content wrapped in a <span> carrying its own font-size (px).

    Rich-text paste sanitizers (Naver, Tistory, ...) commonly preserve
    run-level (span) formatting but strip style attributes off block
    containers (p/li/div) since those aren't "text runs". A <p
    style="font-size:15px"> alone gets its style dropped on paste and falls
    back to the editor's currently active toolbar size; wrapping the run in
    its own <span style="font-size:...px"> survives that filtering.
    """
    return f'<span style="font-size:{size_px}px;">{_inline(text)}</span>'


def _table_html(data: dict) -> str:
    head = "".join(f'<th style="{_CELL}background:#f0f0f0;">{html.escape(str(h))}</th>'
                   for h in data["headers"])
    rows = "".join(
        "<tr>" + "".join(f'<td style="{_CELL}">{html.escape(str(v))}</td>' for v in row) + "</tr>"
        for row in data["rows"])
    return f'<table style="{_TABLE}"><tr>{head}</tr>{rows}</table>'


def _img_html(png_path: Path, caption: str | None) -> str:
    png_path = Path(png_path)
    b64 = base64.b64encode(png_path.read_bytes()).decode("ascii")
    with Image.open(png_path) as im:
        native_w, native_h = im.size
    display_w = min(_IMG_DISPLAY_WIDTH, native_w)
    display_h = round(native_h * display_w / native_w)
    img = (f'<img src="data:image/png;base64,{b64}" '
           f'width="{display_w}" height="{display_h}" '
           f'style="max-width:100%;height:auto;" alt="">')
    cap = (f'<p style="font-size:11px;color:#666;">'
           f'<span style="font-size:11px;color:#666;">{html.escape(caption)}</span></p>'
           if caption else "")
    return f"<figure style=\"margin:1em 0;\">{img}{cap}</figure>"


def build_html(*, body_md: str, table_specs: dict[str, dict],
               chart_images: dict[str, Path], chart_captions: dict[str, str] | None = None,
               sources: list[str], out_path: Path,
               title_candidates: list[str] | None = None) -> Path:
    captions = chart_captions or {}
    parts: list[str] = []
    if title_candidates:
        comment_lines = ["제목 후보 (발행 시 택1)"] + [
            f"{i}. {t}" for i, t in enumerate(title_candidates, 1)]
        # HTML comments are not rendered and not selectable in the page, so
        # they survive "select all -> copy -> paste" without polluting the
        # pasted content, but stay visible via view-source for the human.
        parts.append("<!--\n" + "\n".join(comment_lines) + "\n-->")
    parts.append(f'<div style="{_STYLE}">')
    bullet_open = False

    def close_bullets():
        nonlocal bullet_open
        if bullet_open:
            parts.append("</ul>")
            bullet_open = False

    for line in body_md.splitlines():
        m = _CHART_RE.match(line.strip())
        if m:
            close_bullets()
            cid = m.group("id")
            if cid in table_specs:
                parts.append(_table_html(table_specs[cid]["data"]))
            elif cid in chart_images:
                parts.append(_img_html(chart_images[cid], captions.get(cid)))
            else:
                parts.append(f'<p style="font-size:15px;">{_run(f"[도표 누락: {cid}]", 15)}</p>')
            continue
        if line.startswith("### "):
            close_bullets()
            parts.append(f'<h3 style="{_H3}">{_inline(line[4:])}</h3>')
        elif line.startswith("## "):
            close_bullets()
            parts.append(f'<h2 style="{_H2}">{_inline(line[3:])}</h2>')
        elif line.startswith("# "):
            close_bullets()
            parts.append(f'<h1 style="{_H1}">{_inline(line[2:])}</h1>')
        elif line.startswith("- "):
            if not bullet_open:
                parts.append('<ul style="margin:0.5em 0 0.5em 1.2em;">')
                bullet_open = True
            parts.append(f'<li style="font-size:15px;">{_run(line[2:], 15)}</li>')
        elif line.strip():
            close_bullets()
            parts.append(f'<p style="font-size:15px;">{_run(line, 15)}</p>')
    close_bullets()

    if sources:
        parts.append(f'<h2 style="{_H2}">출처</h2>')
        for s in sources:
            parts.append(f'<p style="font-size:12px;">{_run(s, 12)}</p>')
    parts.append("</div>")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = ("<!DOCTYPE html><html lang=\"ko\"><head><meta charset=\"utf-8\">"
           "<title>blog draft</title></head><body>" + "\n".join(parts) + "</body></html>")
    out_path.write_text(doc, encoding="utf-8")
    return out_path
