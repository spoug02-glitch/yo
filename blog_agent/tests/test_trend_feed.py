from blog_agent import trend_feed


class _FakeResp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"status={self.status_code}")

    def json(self):
        return self._payload


class _FakeHttp:
    def __init__(self, resp):
        self._resp = resp
        self.calls = []

    def get(self, url, headers=None, timeout=None):
        self.calls.append(url)
        return self._resp


def test_fetch_trending_keywords_returns_ranked_keywords():
    payload = {"top10": [
        {"rank": 2, "keyword": "두번째"},
        {"rank": 1, "keyword": "첫번째"},
        {"rank": 3, "keyword": "세번째"},
    ]}
    http = _FakeHttp(_FakeResp(payload))
    result = trend_feed.fetch_trending_keywords(http=http)
    assert result == ["첫번째", "두번째", "세번째"]
    assert http.calls == ["https://api.signal.bz/news/realtime"]


def test_fetch_trending_keywords_skips_rows_without_keyword():
    payload = {"top10": [{"rank": 1, "keyword": "정상"}, {"rank": 2}]}
    http = _FakeHttp(_FakeResp(payload))
    assert trend_feed.fetch_trending_keywords(http=http) == ["정상"]


def test_fetch_trending_keywords_returns_empty_on_http_error():
    http = _FakeHttp(_FakeResp({}, status=500))
    assert trend_feed.fetch_trending_keywords(http=http) == []


def test_fetch_trending_keywords_returns_empty_on_missing_top10():
    http = _FakeHttp(_FakeResp({"naver": []}))
    assert trend_feed.fetch_trending_keywords(http=http) == []


def test_fetch_trending_keywords_survives_top10_not_a_list():
    # API schema drift: top10 becomes a dict/string/number instead of a list
    for bad_top10 in ({"unexpected": "shape"}, "not a list", 42, None):
        http = _FakeHttp(_FakeResp({"top10": bad_top10}))
        assert trend_feed.fetch_trending_keywords(http=http) == []


def test_fetch_trending_keywords_survives_non_dict_rows():
    # API schema drift: rows are bare strings/numbers instead of {"rank","keyword"} dicts
    http = _FakeHttp(_FakeResp({"top10": ["그냥 문자열", 123, None]}))
    assert trend_feed.fetch_trending_keywords(http=http) == []


def test_fetch_trending_keywords_survives_mixed_valid_and_malformed_rows():
    # one good row alongside rows missing fields or of the wrong type entirely
    payload = {"top10": [
        {"rank": 1, "keyword": "정상"},
        {"rank": 2},                 # keyword 필드 자체가 없어짐
        "완전히 다른 모양",              # 항목이 dict조차 아님
        {"keyword": "순위없음"},        # rank 필드가 없어짐 (기본값으로 처리돼야 함)
    ]}
    http = _FakeHttp(_FakeResp(payload))
    result = trend_feed.fetch_trending_keywords(http=http)
    assert "정상" in result and "순위없음" in result
    assert len(result) == 2


def test_fetch_trending_keywords_survives_top_level_response_not_a_dict():
    # API schema drift: whole response becomes a bare list instead of an object
    class _ListResp:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return ["unexpected", "top-level", "array"]

    class _Http:
        def get(self, url, headers=None, timeout=None):
            return _ListResp()

    assert trend_feed.fetch_trending_keywords(http=_Http()) == []
