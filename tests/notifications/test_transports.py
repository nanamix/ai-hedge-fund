import json
from pathlib import Path

from src.notifications.transports import DEFAULT_HERMES_QUEUE_PATH, QueueHermesTransport, choose_transport


def test_choose_transport_prefers_hermes_queue(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_QUEUE_PATH", str(tmp_path))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fallback-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "fallback-chat")

    transport = choose_transport(dry_run=False)

    assert isinstance(transport, QueueHermesTransport)


def test_choose_transport_uses_default_hermes_queue_when_no_env(monkeypatch):
    monkeypatch.delenv("HERMES_QUEUE_PATH", raising=False)
    monkeypatch.delenv("HERMES_NOTIFY_COMMAND", raising=False)
    monkeypatch.delenv("HERMES_NOTIFY_URL", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    transport = choose_transport(dry_run=False)

    assert isinstance(transport, QueueHermesTransport)
    assert transport.queue_path == DEFAULT_HERMES_QUEUE_PATH


def test_queue_hermes_transport_writes_message(tmp_path):
    transport = QueueHermesTransport(tmp_path)

    result = transport.send("hello")

    files = list(Path(tmp_path).glob("*.json"))
    assert result.delivered is True
    assert result.transport == "hermes_queue"
    assert len(files) == 1
    assert "hello" in files[0].read_text(encoding="utf-8")


def test_queue_hermes_transport_writes_structured_payload(tmp_path):
    transport = QueueHermesTransport(tmp_path)

    result = transport.send_payload({
        "kind": "summary",
        "title": "Flow Summary",
        "summary": "장중 요약",
        "actions": ["관망 유지"],
    })

    files = list(Path(tmp_path).glob("*.json"))
    assert result.delivered is True
    assert len(files) == 1
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert payload["channel"] == "telegram"
    assert payload["kind"] == "summary"
    assert payload["actions"] == ["관망 유지"]
