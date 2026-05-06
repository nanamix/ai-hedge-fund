from src.notifications.state import FlowStateStore


def test_state_store_detects_duplicate_message(tmp_path):
    path = tmp_path / "state.json"
    store = FlowStateStore(path)

    assert store.is_duplicate("09:00", "hello") is False
    store.record("09:00", "hello")
    assert store.is_duplicate("09:00", "hello") is True
    assert store.is_duplicate("12:30", "hello") is False
