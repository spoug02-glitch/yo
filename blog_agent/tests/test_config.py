from blog_agent import config


def test_load_config_preserves_unverified_flags():
    cfg = config.load_config()
    assert cfg["score_floor"]["unverified"] is True
    assert cfg["news"]["freshness_zero_hours"]["value"] == 72


def test_value_unwraps_dotted_key():
    cfg = config.load_config()
    assert config.value(cfg, "score_floor") == 60
    assert config.value(cfg, "news.freshness_zero_hours") == 72
    assert config.value(cfg, "ledger.cooldown_days") == 60
