from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import requests

from src.notifications.models import NotificationResult


DEFAULT_HERMES_QUEUE_PATH = Path("/Users/hajinyoung/Dev/ai-hedge-fund/.cache/hermes-alerts")
DEFAULT_HERMES_HOME = Path.home() / ".hermes"


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


class DryRunTransport:
    name = "dry_run"

    def send(self, message: str) -> NotificationResult:
        print(message)
        return NotificationResult(transport=self.name, delivered=True, detail="printed")


class QueueHermesTransport:
    name = "hermes_queue"

    def __init__(self, queue_path: str | Path):
        self.queue_path = Path(queue_path)

    def send(self, message: str) -> NotificationResult:
        self.queue_path.mkdir(parents=True, exist_ok=True)
        path = self.queue_path / f"ai-hedge-flow-{int(time.time() * 1000)}.json"
        payload = {"channel": "telegram", "text": message}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return NotificationResult(transport=self.name, delivered=True, detail=str(path))


class DirectHermesTransport:
    name = "hermes_direct"

    def __init__(
        self,
        hermes_home: str | Path | None = None,
        agent_dir: str | Path | None = None,
        python_path: str | Path | None = None,
        target: str = "telegram",
    ):
        self.hermes_home = Path(hermes_home or os.getenv("HERMES_HOME", DEFAULT_HERMES_HOME))
        self.agent_dir = Path(agent_dir or os.getenv("HERMES_AGENT_DIR", self.hermes_home / "hermes-agent"))
        self.python_path = Path(python_path or os.getenv("HERMES_PYTHON", self.agent_dir / "venv/bin/python"))
        self.target = os.getenv("HERMES_NOTIFY_TARGET", target)

    def is_available(self) -> bool:
        return (
            self.python_path.exists()
            and os.access(self.python_path, os.X_OK)
            and (self.agent_dir / "tools/send_message_tool.py").exists()
        )

    def send(self, message: str) -> NotificationResult:
        completed = subprocess.run(
            [
                str(self.python_path),
                "-c",
                _DIRECT_HERMES_SCRIPT,
                self.target,
                message,
            ],
            cwd=str(self.agent_dir),
            text=True,
            capture_output=True,
            check=False,
            timeout=45,
            env=self._env(),
        )
        detail = completed.stderr.strip() or completed.stdout.strip()
        delivered = completed.returncode == 0 and _stdout_success(completed.stdout)
        return NotificationResult(transport=self.name, delivered=delivered, detail=detail)

    def _env(self) -> dict[str, str]:
        env = os.environ.copy()
        env_path = self.hermes_home / ".env"
        if env_path.exists():
            env.update(_read_env_file(env_path))
        return env


_DIRECT_HERMES_SCRIPT = r"""
import json
import sys

from tools.send_message_tool import send_message_tool

target = sys.argv[1]
message = sys.argv[2]
raw = send_message_tool({"action": "send", "target": target, "message": message})
print(raw)
result = json.loads(raw)
if not result.get("success"):
    raise SystemExit(1)
"""


def _stdout_success(stdout: str) -> bool:
    try:
        return bool(json.loads(stdout.strip()).get("success"))
    except json.JSONDecodeError:
        return False


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


class CommandHermesTransport:
    name = "hermes_command"

    def __init__(self, command: str):
        self.command = command

    def send(self, message: str) -> NotificationResult:
        completed = subprocess.run(
            [self.command, message],
            text=True,
            capture_output=True,
            check=False,
        )
        return NotificationResult(
            transport=self.name,
            delivered=completed.returncode == 0,
            detail=completed.stderr.strip() or completed.stdout.strip(),
        )


class HttpHermesTransport:
    name = "hermes_http"

    def __init__(self, url: str):
        self.url = url

    def send(self, message: str) -> NotificationResult:
        response = requests.post(self.url, json={"channel": "telegram", "text": message}, timeout=10)
        return NotificationResult(
            transport=self.name,
            delivered=200 <= response.status_code < 300,
            detail=f"status={response.status_code}",
        )


class TelegramTransport:
    name = "telegram"

    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id

    def send(self, message: str) -> NotificationResult:
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        response = requests.post(url, data={"chat_id": self.chat_id, "text": message}, timeout=10)
        return NotificationResult(
            transport=self.name,
            delivered=200 <= response.status_code < 300,
            detail=f"status={response.status_code}",
        )


def choose_transport(dry_run: bool = False):
    if dry_run:
        return DryRunTransport()
    if queue_path := os.getenv("HERMES_QUEUE_PATH"):
        return QueueHermesTransport(queue_path)
    if command := os.getenv("HERMES_NOTIFY_COMMAND"):
        return CommandHermesTransport(command)
    if url := os.getenv("HERMES_NOTIFY_URL"):
        return HttpHermesTransport(url)
    direct = DirectHermesTransport()
    if not _truthy(os.getenv("HERMES_DIRECT_DISABLED")) and direct.is_available():
        return direct
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        return TelegramTransport(token, chat_id)
    return QueueHermesTransport(DEFAULT_HERMES_QUEUE_PATH)
