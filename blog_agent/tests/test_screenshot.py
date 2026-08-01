from pathlib import Path

from PIL import Image

from blog_agent import screenshot


def test_autotrim_crops_to_content_with_padding(tmp_path):
    # 200x200 white page with a 40x40 red square content block at (80,80)
    im = Image.new("RGB", (200, 200), "white")
    for x in range(80, 120):
        for y in range(80, 120):
            im.putpixel((x, y), (200, 30, 30))
    raw = tmp_path / "raw.png"
    im.save(raw)

    out = screenshot.autotrim(raw, tmp_path / "trimmed.png", pad=10)
    trimmed = Image.open(out)
    # content bbox (80,80)-(120,120) + 10px padding each side => (70,70)-(130,130)
    assert trimmed.size == (60, 60)


def test_autotrim_keeps_full_image_when_uniform(tmp_path):
    im = Image.new("RGB", (50, 50), "white")
    raw = tmp_path / "raw.png"
    im.save(raw)
    out = screenshot.autotrim(raw, tmp_path / "t.png")
    assert Image.open(out).size == (50, 50)


def test_find_browser_returns_none_when_no_candidates_exist(tmp_path):
    fake = str(tmp_path / "no_such_browser.exe")
    assert screenshot.find_browser([fake]) is None


def test_find_browser_returns_existing_candidate(tmp_path):
    real = tmp_path / "browser.exe"
    real.write_text("stub")
    assert screenshot.find_browser([str(real)]) == str(real)


def test_capture_card_invokes_browser_and_trims(tmp_path):
    html = tmp_path / "card.html"
    html.write_text("<html></html>", encoding="utf-8")
    browser = tmp_path / "chrome.exe"
    browser.write_text("stub")

    calls = []

    def fake_run(cmd, check, capture_output):
        calls.append(cmd)
        # simulate chrome writing the raw screenshot it was asked for
        raw_arg = next(a for a in cmd if a.startswith("--screenshot="))
        raw_path = Path(raw_arg.split("=", 1)[1])
        im = Image.new("RGB", (60, 60), "white")
        for x in range(20, 40):
            for y in range(20, 40):
                im.putpixel((x, y), (0, 100, 0))
        im.save(raw_path)

    out = screenshot.capture_card(html, tmp_path / "out.png", browser=str(browser), run=fake_run)
    assert out.exists()
    assert len(calls) == 1
    assert not out.with_suffix(".raw.png").exists()  # raw cleaned up


def test_capture_card_default_viewport_clears_standard_card_layout_width(tmp_path):
    # Regression: --screenshot clips anything outside --window-size (no
    # scroll/scale), so a viewport sized to exactly the card's own
    # width silently cropped page-level body padding around it (a 1000px
    # card + 40px body padding each side needs 1080px; capturing at 1000
    # cut the last 80px off every card). Defaults must clear that with margin.
    html = tmp_path / "card.html"
    html.write_text("<html></html>", encoding="utf-8")
    browser = tmp_path / "chrome.exe"
    browser.write_text("stub")
    calls = []

    def fake_run(cmd, check, capture_output):
        calls.append(cmd)
        raw_path = Path(next(a for a in cmd if a.startswith("--screenshot=")).split("=", 1)[1])
        Image.new("RGB", (10, 10), "white").save(raw_path)

    screenshot.capture_card(html, tmp_path / "out.png", browser=str(browser), run=fake_run)
    size_arg = next(a for a in calls[0] if a.startswith("--window-size="))
    width, height = (int(v) for v in size_arg.split("=", 1)[1].split(","))
    STANDARD_CARD_WIDTH_WITH_BODY_PADDING = 1000 + 2 * 40
    assert width > STANDARD_CARD_WIDTH_WITH_BODY_PADDING
    assert height > 1400
