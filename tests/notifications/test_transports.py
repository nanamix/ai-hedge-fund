from pathlib import Path

from src.notifications.models import NotificationResult
from src.notifications.transports import (
    DEFAULT_HERMES_QUEUE_PATH,
    DirectHermesTransport,
    QueueHermesTransport,
    choose_transport,
)


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
    monkeypatch.setenv("HERMES_DIRECT_DISABLED", "1")

    transport = choose_transport(dry_run=False)

    assert isinstance(transport, QueueHermesTransport)
    assert transport.queue_path == DEFAULT_HERMES_QUEUE_PATH


def test_choose_transport_uses_direct_hermes_when_available(tmp_path, monkeypatch):
    hermes_home = tmp_path / ".hermes"
    python_path = hermes_home / "hermes-agent/venv/bin/python"
    tool_path = hermes_home / "hermes-agent/tools/send_message_tool.py"
    python_path.parent.mkdir(parents=True)
    tool_path.parent.mkdir(parents=True)
    python_path.write_text("#!/bin/sh\n", encoding="utf-8")
    python_path.chmod(0o755)
    tool_path.write_text("", encoding="utf-8")

    monkeypatch.delenv("HERMES_QUEUE_PATH", raising=False)
    monkeypatch.delenv("HERMES_NOTIFY_COMMAND", raising=False)
    monkeypatch.delenv("HERMES_NOTIFY_URL", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("HERMES_DIRECT_DISABLED", raising=False)
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))

    transport = choose_transport(dry_run=False)

    assert isinstance(transport, DirectHermesTransport)


def test_direct_hermes_transport_sends_with_home_env(tmp_path, monkeypatch):
    hermes_home = tmp_path / ".hermes"
    agent_dir = hermes_home / "hermes-agent"
    python_path = agent_dir / "venv/bin/python"
    python_path.parent.mkdir(parents=True)
    agent_dir.mkdir(exist_ok=True)
    (hermes_home / ".env").write_text("TELEGRAM_HOME_CHANNEL=144112350\n", encoding="utf-8")
    python_path.write_text("#!/bin/sh\n", encoding="utf-8")
    python_path.chmod(0o755)

    calls = []

    def fake_run(command, **kwargs):
        calls.append({"command": command, **kwargs})
        return type(
            "Completed",
            (),
            {
                "returncode": 0,
                "stdout": '{"success": true, "platform": "telegram"}',
                "stderr": "",
            },
        )()

    monkeypatch.setattr("src.notifications.transports.subprocess.run", fake_run)

    result = DirectHermesTransport(
        hermes_home=hermes_home,
        agent_dir=agent_dir,
        python_path=python_path,
    ).send("hello")

    assert result == NotificationResult(transport="hermes_direct", delivered=True, detail='{"success": true, "platform": "telegram"}')
    assert calls[0]["cwd"] == str(agent_dir)
    assert calls[0]["env"]["TELEGRAM_HOME_CHANNEL"] == "144112350"


def test_queue_hermes_transport_writes_message(tmp_path):
    transport = QueueHermesTransport(tmp_path)

    result = transport.send("hello")

    files = list(Path(tmp_path).glob("*.json"))
    assert result.delivered is True
    assert result.transport == "hermes_queue"
    assert len(files) == 1
    assert "hello" in files[0].read_text(encoding="utf-8")
