from datetime import datetime, timedelta, timezone

from blog_agent import ledger

NOW = datetime(2026, 7, 29, 12, 0, 0)


def test_normalize_strips_spaces_and_particles():
    assert ledger.normalize_longtail("AICE 자격증 을") == ledger.normalize_longtail("AICE자격증")


def test_record_then_blocked_within_cooldown(tmp_path):
    store = ledger.JsonLedgerStore(tmp_path / "l.json")
    store.record("cert", "AICE", "AICE 기초 가이드", NOW)
    assert store.is_blocked("AICE 기초 가이드", NOW + timedelta(days=30), 60) is True


def test_not_blocked_after_cooldown(tmp_path):
    store = ledger.JsonLedgerStore(tmp_path / "l.json")
    store.record("cert", "AICE", "AICE 기초 가이드", NOW)
    assert store.is_blocked("AICE 기초 가이드", NOW + timedelta(days=61), 60) is False


def test_different_longtail_not_blocked(tmp_path):
    store = ledger.JsonLedgerStore(tmp_path / "l.json")
    store.record("cert", "AICE", "AICE 기초 가이드", NOW)
    assert store.is_blocked("AICE Associate 응시료", NOW + timedelta(days=1), 60) is False


def test_normalize_strips_two_char_particle():
    assert ledger.normalize_longtail("AICE 자격증 으로") == ledger.normalize_longtail("AICE자격증")


def test_persistence_round_trip(tmp_path):
    path = tmp_path / "l.json"
    store1 = ledger.JsonLedgerStore(path)
    store1.record("cert", "AICE", "AICE 기초 가이드", NOW)

    store2 = ledger.JsonLedgerStore(path)
    assert store2.is_blocked("AICE 기초 가이드", NOW + timedelta(days=30), 60) is True


def test_record_aware_then_is_blocked_naive_no_exception(tmp_path):
    aware_now = NOW.replace(tzinfo=timezone.utc)
    store = ledger.JsonLedgerStore(tmp_path / "l.json")
    store.record("cert", "AICE", "AICE 기초 가이드", aware_now)
    # naive `now`, no tzinfo — must not raise and must still block within cooldown
    assert store.is_blocked("AICE 기초 가이드", NOW + timedelta(days=30), 60) is True
    assert store.is_blocked("AICE 기초 가이드", NOW + timedelta(days=61), 60) is False


def test_record_naive_then_is_blocked_aware_no_exception(tmp_path):
    store = ledger.JsonLedgerStore(tmp_path / "l.json")
    store.record("cert", "AICE", "AICE 기초 가이드", NOW)
    aware_later = (NOW + timedelta(days=30)).replace(tzinfo=timezone.utc)
    aware_expired = (NOW + timedelta(days=61)).replace(tzinfo=timezone.utc)
    assert store.is_blocked("AICE 기초 가이드", aware_later, 60) is True
    assert store.is_blocked("AICE 기초 가이드", aware_expired, 60) is False
