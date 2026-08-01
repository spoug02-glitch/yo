from datetime import datetime, timezone

from blog_agent import news_feeds


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200

    def json(self):
        return self._payload

    def raise_for_status(self):
        pass


class _FakeHttp:
    def __init__(self, mapping):
        self.mapping = mapping

    def get(self, url, timeout=10):
        return _FakeResp(self.mapping[url])


def test_fetch_hackernews_maps_items():
    base = "https://hacker-news.firebaseio.com/v0"
    http = _FakeHttp({
        f"{base}/topstories.json": [101, 102],
        f"{base}/item/101.json": {
            "id": 101, "title": "OpenAI ships thing", "score": 240,
            "url": "https://x.com/a", "time": 1753000000, "type": "story",
        },
        f"{base}/item/102.json": {
            "id": 102, "title": "Rust 2.0", "score": 88,
            "url": "https://x.com/b", "time": 1753100000, "type": "story",
        },
    })
    items = news_feeds.fetch_hackernews(top_n=2, http=http)
    assert [i.title for i in items] == ["OpenAI ships thing", "Rust 2.0"]
    assert items[0].points == 240
    assert items[0].source == "hackernews"
    assert items[0].published_utc == datetime.fromtimestamp(1753000000, tz=timezone.utc)


def test_fetch_rss_maps_entries():
    class _Feed:
        entries = [
            type("E", (), {"title": "Verge story", "link": "https://v/1",
                            "published_parsed": (2026, 7, 28, 9, 0, 0, 0, 0, 0)})()
        ]

    def fake_parse(url):
        return _Feed()

    items = news_feeds.fetch_rss(["https://verge/rss"], parse=fake_parse)
    assert items[0].title == "Verge story"
    assert items[0].source == "https://verge/rss"
    assert items[0].published_utc.year == 2026


def test_fetch_hackernews_skips_non_story_and_missing_title():
    base = "https://hacker-news.firebaseio.com/v0"
    http = _FakeHttp({
        f"{base}/topstories.json": [201, 202, 203],
        f"{base}/item/201.json": {
            "id": 201, "type": "job", "score": 10,
            "url": "https://x.com/job", "time": 1753000000,
        },
        f"{base}/item/202.json": {
            "id": 202, "type": "story", "score": 50,
            "url": "https://x.com/notitle", "time": 1753000000,
        },
        f"{base}/item/203.json": {
            "id": 203, "title": "Valid story", "type": "story", "score": 100,
            "url": "https://x.com/valid", "time": 1753000000,
        },
    })
    items = news_feeds.fetch_hackernews(top_n=3, http=http)
    assert len(items) == 1
    assert items[0].title == "Valid story"


def test_fetch_hackernews_url_falls_back_to_hn_item_page():
    base = "https://hacker-news.firebaseio.com/v0"
    http = _FakeHttp({
        f"{base}/topstories.json": [301],
        f"{base}/item/301.json": {
            "id": 301, "title": "No URL story", "type": "story", "score": 75,
            "time": 1753000000,
        },
    })
    items = news_feeds.fetch_hackernews(top_n=1, http=http)
    assert items[0].url == "https://news.ycombinator.com/item?id=301"
    assert items[0].id == "301"


def test_fetch_rss_missing_published_parsed_gives_none():
    class _Feed:
        entries = [
            type("E", (), {"title": "No date story", "link": "https://v/2"})()
        ]

    def fake_parse(url):
        return _Feed()

    items = news_feeds.fetch_rss(["https://verge/rss"], parse=fake_parse)
    assert items[0].title == "No date story"
    assert items[0].published_utc is None


class _BrokenHttp:
    def get(self, url, timeout=10):
        raise ConnectionError("HN down")


def test_gather_news_survives_hackernews_failure():
    from blog_agent import config

    class _Feed:
        entries = [
            type("E", (), {"title": "RSS survivor", "link": "https://v/3",
                            "published_parsed": (2026, 7, 28, 9, 0, 0, 0, 0, 0)})()
        ]

    cfg = config.load_config()
    items, failures = news_feeds.gather_news(cfg, http=_BrokenHttp(), parse=lambda url: _Feed())
    assert [i.title for i in items].count("RSS survivor") == len(config.value(cfg, "rss_feeds"))
    assert len(failures) == 1 and failures[0].startswith("hackernews:")


def test_gather_news_isolates_single_rss_failure():
    from blog_agent import config

    base = "https://hacker-news.firebaseio.com/v0"
    http = _FakeHttp({
        f"{base}/topstories.json": [401],
        f"{base}/item/401.json": {"id": 401, "title": "HN ok", "type": "story",
                                   "score": 10, "time": 1753000000, "url": "https://x"},
    })

    class _Feed:
        entries = [
            type("E", (), {"title": "Good feed", "link": "https://v/4",
                            "published_parsed": (2026, 7, 28, 9, 0, 0, 0, 0, 0)})()
        ]

    cfg = config.load_config()
    feeds = config.value(cfg, "rss_feeds")
    bad = feeds[0]

    def flaky_parse(url):
        if url == bad:
            raise ValueError("malformed feed")
        return _Feed()

    items, failures = news_feeds.gather_news(cfg, http=http, parse=flaky_parse)
    titles = [i.title for i in items]
    assert "HN ok" in titles
    assert titles.count("Good feed") == len(feeds) - 1
    assert len(failures) == 1 and bad in failures[0]
