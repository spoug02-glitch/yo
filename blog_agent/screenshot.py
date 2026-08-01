"""Screenshot an HTML/CSS infographic card and autotrim it to its content box.

Used for chart types (bar/donut/flowchart/line) where a designed HTML card
(Codex-authored, following the AICE-style design system) reads far better
than a raw matplotlib plot. `charts.render_chart` (matplotlib) remains
available as a simpler fallback when no browser is present.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageChops

_CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_browser(candidates: list[str] | None = None) -> str | None:
    for path in candidates or _CHROME_CANDIDATES:
        if Path(path).exists():
            return path
    return None


def _raw_screenshot(browser: str, html_path: Path, raw_out: Path,
                    width: int, height: int, scale: int, *, run=subprocess.run) -> None:
    # Chrome's headless --screenshot writer fails silently on relative paths
    # containing non-ASCII characters (observed with a Korean topic-slug
    # folder) -- always pass it an absolute path.
    run([
        browser, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
        f"--force-device-scale-factor={scale}", f"--window-size={width},{height}",
        f"--screenshot={raw_out.resolve()}", html_path.resolve().as_uri(),
    ], check=True, capture_output=True)


def autotrim(raw_path: Path, out_path: Path, *, pad: int = 20) -> Path:
    """Crop a full-viewport screenshot down to its non-background content box."""
    im = Image.open(raw_path).convert("RGB")
    bg = Image.new("RGB", im.size, im.getpixel((2, 2)))
    bbox = ImageChops.difference(im, bg).getbbox()
    cropped = im if bbox is None else im.crop((
        max(0, bbox[0] - pad), max(0, bbox[1] - pad),
        min(im.width, bbox[2] + pad), min(im.height, bbox[3] + pad),
    ))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cropped.save(out_path)
    return out_path


def capture_card(html_path: Path, out_path: Path, *, width: int = 1600, height: int = 2400,
                 scale: int = 2, browser: str | None = None, run=subprocess.run) -> Path:
    """Render html_path headlessly and save an autotrimmed png to out_path.

    `--screenshot` captures exactly the `--window-size` viewport -- anything
    laid out past its edges is clipped at capture time, not scaled or
    scrolled into view. The card design system fixes card width at 1000px,
    but page-level body padding around it (commonly ~40px each side) pushes
    the real required layout width past 1000px; a capture viewport sized to
    exactly the card's own width silently clipped that overflow (observed:
    a bar chart's right-edge amounts and a donut chart's legend column both
    lost their outer margin, reading as "cropped" once pasted). Defaults
    here are generous on both axes -- `autotrim` discards whatever blank
    margin is left over, so oversizing the capture viewport costs nothing.
    """
    chrome = browser or find_browser()
    if chrome is None:
        raise RuntimeError("no headless-capable browser found (Chrome/Edge)")
    out_path = Path(out_path)
    raw = out_path.with_suffix(".raw.png")
    _raw_screenshot(chrome, Path(html_path), raw, width, height, scale, run=run)
    result = autotrim(raw, out_path)
    raw.unlink(missing_ok=True)
    return result
