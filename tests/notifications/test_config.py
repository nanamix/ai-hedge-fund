from src.notifications.config import load_config


def test_load_config_reads_watchlist_and_state_path_from_env(monkeypatch):
    monkeypatch.setenv("AI_HEDGE_FLOW_WATCHLIST", "SPYM, SGOV, AMZN")
    monkeypatch.setenv("AI_HEDGE_FLOW_STATE_PATH", "/tmp/custom-flow-state.json")

    config = load_config()

    assert config.watchlist == ["SPYM", "SGOV", "AMZN"]
    assert str(config.state_path) == "/tmp/custom-flow-state.json"
