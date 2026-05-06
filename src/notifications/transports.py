from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import requests

from src.notifications.models import NotificationResult


DEFAULT_HERMES_QUEUE_PATH = Path("/Users/hajinyoung/Dev/ai-hedge-fund/.cache/hermes-alerts")


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
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        return TelegramTransport(token, chat_id)
    return QueueHermesTransport(DEFAULT_HERMES_QUEUE_PATH)
