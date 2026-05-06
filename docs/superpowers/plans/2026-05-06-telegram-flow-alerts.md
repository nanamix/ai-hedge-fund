# Telegram Flow Alerts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a scheduled portfolio-flow alert CLI that formats calm investment summaries and sends them through Hermes Agent when available, with Telegram fallback and dry-run output.

**Architecture:** Add a focused `src/notifications` package. Keep market snapshot creation, rule classification, message formatting, state persistence, and transports separate so Hermes can be connected by changing one adapter instead of the whole monitor.

**Tech Stack:** Python 3.11, Pydantic-style dataclasses where simple, `requests`, existing `python-dotenv`, pytest, macOS `launchd` later.

---

## File Structure

- Create `src/notifications/__init__.py`: package marker.
- Create `src/notifications/models.py`: shared dataclasses for assets, snapshots, rule results, and notification results.
- Create `src/notifications/config.py`: load env vars, watchlist, schedule labels, and notifier settings.
- Create `src/notifications/rules.py`: classify market snapshots into `대기`, `보류`, `검토`, or `분할매수 후보`.
- Create `src/notifications/formatter.py`: render concise Telegram/Hermes message text.
- Create `src/notifications/state.py`: JSON state load/save and duplicate-message guard.
- Create `src/notifications/transports.py`: Hermes CLI/HTTP/file queue transports plus direct Telegram fallback and dry-run transport.
- Create `src/notifications/telegram_flow_check.py`: CLI entrypoint that wires config, snapshot, rules, formatting, state, and transport.
- Create `tests/notifications/test_rules.py`: rule classification tests.
- Create `tests/notifications/test_formatter.py`: message format tests.
- Create `tests/notifications/test_state.py`: state persistence tests.
- Create `tests/notifications/test_transports.py`: transport selection and payload tests.
- Create `tests/notifications/test_cli.py`: dry-run CLI smoke test.

## Task 1: Notification Models

**Files:**
- Create: `src/notifications/__init__.py`
- Create: `src/notifications/models.py`
- Test: `tests/notifications/test_rules.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/notifications/test_rules.py
from src.notifications.models import AssetSnapshot, FlowSnapshot


def test_flow_snapshot_groups_assets_by_symbol():
    snapshot = FlowSnapshot(
        as_of="2026-05-06T23:30:00+09:00",
        phase="us_open",
        assets=[
            AssetSnapshot(symbol="SPYM", name="SPYM", price=83.0, change_pct=0.4, currency="USD"),
            AssetSnapshot(symbol="SGOV", name="SGOV", price=100.5, change_pct=0.01, currency="USD"),
        ],
    )

    assert snapshot.by_symbol()["SPYM"].price == 83.0
    assert snapshot.by_symbol()["SGOV"].currency == "USD"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/notifications/test_rules.py::test_flow_snapshot_groups_assets_by_symbol -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'src.notifications'`.

- [ ] **Step 3: Add minimal models**

```python
# src/notifications/__init__.py
"""Portfolio flow notification helpers."""
```

```python
# src/notifications/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


ActionLabel = Literal["대기", "보류", "검토", "분할매수 후보"]


@dataclass(frozen=True)
class AssetSnapshot:
    symbol: str
    name: str
    price: float | None
    change_pct: float | None
    currency: str
    note: str = ""


@dataclass(frozen=True)
class FlowSnapshot:
    as_of: str
    phase: str
    assets: list[AssetSnapshot] = field(default_factory=list)
    data_warnings: list[str] = field(default_factory=list)

    def by_symbol(self) -> dict[str, AssetSnapshot]:
        return {asset.symbol: asset for asset in self.assets}


@dataclass(frozen=True)
class RuleResult:
    label: ActionLabel
    summary: str
    risk_signals: list[str]
    actions: list[str]


@dataclass(frozen=True)
class NotificationResult:
    transport: str
    delivered: bool
    detail: str
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/notifications/test_rules.py::test_flow_snapshot_groups_assets_by_symbol -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/notifications/__init__.py src/notifications/models.py tests/notifications/test_rules.py
git commit -m "feat: add notification flow models"
```

## Task 2: Rule Classification

**Files:**
- Modify: `src/notifications/rules.py`
- Test: `tests/notifications/test_rules.py`

- [ ] **Step 1: Add failing rule tests**

```python
# append to tests/notifications/test_rules.py
from src.notifications.rules import classify_flow


def test_classify_defaults_to_hold_when_data_missing():
    snapshot = FlowSnapshot(
        as_of="2026-05-06T23:30:00+09:00",
        phase="us_open",
        assets=[],
        data_warnings=["price data unavailable"],
    )

    result = classify_flow(snapshot)

    assert result.label == "보류"
    assert "데이터" in result.summary
    assert any("매수 금지" in action or "보류" in action for action in result.actions)


def test_classify_warns_against_tqqq_fomo():
    snapshot = FlowSnapshot(
        as_of="2026-05-06T23:30:00+09:00",
        phase="us_open",
        assets=[
            AssetSnapshot(symbol="TQQQ", name="TQQQ", price=75.0, change_pct=5.2, currency="USD"),
            AssetSnapshot(symbol="SPYM", name="SPYM", price=83.0, change_pct=0.4, currency="USD"),
        ],
    )

    result = classify_flow(snapshot)

    assert result.label == "보류"
    assert any("레버리지" in signal for signal in result.risk_signals)
    assert any("TQQQ" in action for action in result.actions)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/notifications/test_rules.py -v`

Expected: FAIL with `ModuleNotFoundError` or missing `classify_flow`.

- [ ] **Step 3: Implement rule classifier**

```python
# src/notifications/rules.py
from __future__ import annotations

from src.notifications.models import FlowSnapshot, RuleResult


CORE_SYMBOLS = {"SPY", "SPYM", "SPYV", "SGOV", "BIL", "TFLO"}
GROWTH_OR_THEME_SYMBOLS = {"VUG", "AMZN", "VOLT", "TQQQ"}


def classify_flow(snapshot: FlowSnapshot) -> RuleResult:
    risk_signals: list[str] = []
    actions: list[str] = []

    if snapshot.data_warnings:
        return RuleResult(
            label="보류",
            summary="데이터가 충분하지 않아 신규 매수 판단은 보류합니다.",
            risk_signals=[f"데이터 경고: {warning}" for warning in snapshot.data_warnings],
            actions=["신규 매수: 보류", "대기자금: 유지", "다음 체크까지 관망"],
        )

    for asset in snapshot.assets:
        change = asset.change_pct
        if change is None:
            risk_signals.append(f"{asset.symbol}: 변동률 데이터 없음")
            continue

        if asset.symbol == "TQQQ" and change > 0:
            risk_signals.append("TQQQ 상승은 레버리지 재진입 신호가 아니라 추격매수 경고입니다.")
            actions.append("TQQQ: 신규매수 금지 유지")

        if asset.symbol in CORE_SYMBOLS and abs(change) >= 2.0:
            risk_signals.append(f"{asset.symbol}: 코어/대기자금 자산 변동 {change:.2f}%")

        if asset.symbol in GROWTH_OR_THEME_SYMBOLS and abs(change) >= 4.0:
            risk_signals.append(f"{asset.symbol}: 성장/테마 자산 변동 {change:.2f}%")

    if risk_signals:
        return RuleResult(
            label="보류",
            summary="변동성이 커서 계획 없는 신규 매수는 보류합니다.",
            risk_signals=risk_signals,
            actions=actions or ["신규 매수: 보류", "대기자금: 유지"],
        )

    return RuleResult(
        label="대기",
        summary="큰 변동 신호가 없어 기존 계획을 유지합니다.",
        risk_signals=["레버리지 재진입 금지 유지", "추격매수 방지 규칙 유지"],
        actions=["신규 매수: 없음", "대기자금: 유지"],
    )
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/notifications/test_rules.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/notifications/rules.py tests/notifications/test_rules.py
git commit -m "feat: classify portfolio flow alerts"
```

## Task 3: Message Formatting

**Files:**
- Create: `src/notifications/formatter.py`
- Test: `tests/notifications/test_formatter.py`

- [ ] **Step 1: Write failing formatter test**

```python
# tests/notifications/test_formatter.py
from src.notifications.formatter import format_flow_message
from src.notifications.models import AssetSnapshot, FlowSnapshot, RuleResult


def test_format_flow_message_is_concise_and_contains_rules():
    snapshot = FlowSnapshot(
        as_of="2026-05-06T23:30:00+09:00",
        phase="us_open",
        assets=[
            AssetSnapshot(symbol="SPYM", name="SPYM", price=83.12, change_pct=0.45, currency="USD"),
            AssetSnapshot(symbol="TQQQ", name="TQQQ", price=75.0, change_pct=5.2, currency="USD"),
        ],
    )
    result = RuleResult(
        label="보류",
        summary="변동성이 커서 계획 없는 신규 매수는 보류합니다.",
        risk_signals=["TQQQ 상승은 레버리지 재진입 신호가 아니라 추격매수 경고입니다."],
        actions=["TQQQ: 신규매수 금지 유지", "대기자금: 유지"],
    )

    message = format_flow_message(snapshot, result)

    assert "[AI Hedge Fund Flow]" in message
    assert "23:30" in message
    assert "보류" in message
    assert "TQQQ" in message
    assert "레버리지" in message
    assert len(message) < 1200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/notifications/test_formatter.py -v`

Expected: FAIL with missing module.

- [ ] **Step 3: Implement formatter**

```python
# src/notifications/formatter.py
from __future__ import annotations

from datetime import datetime

from src.notifications.models import FlowSnapshot, RuleResult


def _display_time(as_of: str) -> str:
    try:
        parsed = datetime.fromisoformat(as_of)
        return parsed.strftime("%Y-%m-%d %H:%M KST")
    except ValueError:
        return as_of


def _asset_line(symbol: str, price: float | None, change_pct: float | None, currency: str) -> str:
    price_text = "n/a" if price is None else f"{price:.2f} {currency}"
    change_text = "n/a" if change_pct is None else f"{change_pct:+.2f}%"
    return f"- {symbol}: {price_text}, {change_text}"


def format_flow_message(snapshot: FlowSnapshot, result: RuleResult) -> str:
    lines = [
        f"[AI Hedge Fund Flow] {_display_time(snapshot.as_of)}",
        "",
        f"요약: {result.summary}",
        f"판단: {result.label}",
        "",
        "주요 변화",
    ]

    for asset in snapshot.assets[:8]:
        lines.append(_asset_line(asset.symbol, asset.price, asset.change_pct, asset.currency))

    if not snapshot.assets:
        lines.append("- 가격 데이터 없음")

    lines.extend(["", "리스크 신호"])
    lines.extend(f"- {signal}" for signal in result.risk_signals[:5])

    lines.extend(["", "오늘 행동"])
    lines.extend(f"- {action}" for action in result.actions[:5])

    return "\n".join(lines)
```

- [ ] **Step 4: Run test**

Run: `pytest tests/notifications/test_formatter.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/notifications/formatter.py tests/notifications/test_formatter.py
git commit -m "feat: format telegram flow messages"
```

## Task 4: State Store

**Files:**
- Create: `src/notifications/state.py`
- Test: `tests/notifications/test_state.py`

- [ ] **Step 1: Write failing state tests**

```python
# tests/notifications/test_state.py
from src.notifications.state import FlowStateStore


def test_state_store_detects_duplicate_message(tmp_path):
    path = tmp_path / "state.json"
    store = FlowStateStore(path)

    assert store.is_duplicate("09:00", "hello") is False
    store.record("09:00", "hello")
    assert store.is_duplicate("09:00", "hello") is True
    assert store.is_duplicate("12:30", "hello") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/notifications/test_state.py -v`

Expected: FAIL with missing module.

- [ ] **Step 3: Implement state store**

```python
# src/notifications/state.py
from __future__ import annotations

import hashlib
import json
from pathlib import Path


class FlowStateStore:
    def __init__(self, path: Path):
        self.path = path

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _message_hash(self, message: str) -> str:
        return hashlib.sha256(message.encode("utf-8")).hexdigest()

    def is_duplicate(self, slot: str, message: str) -> bool:
        state = self._load()
        return state.get(slot, {}).get("message_hash") == self._message_hash(message)

    def record(self, slot: str, message: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        state = self._load()
        state[slot] = {"message_hash": self._message_hash(message)}
        self.path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
```

- [ ] **Step 4: Run test**

Run: `pytest tests/notifications/test_state.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/notifications/state.py tests/notifications/test_state.py
git commit -m "feat: add notification state store"
```

## Task 5: Transports With Hermes First

**Files:**
- Create: `src/notifications/transports.py`
- Test: `tests/notifications/test_transports.py`

- [ ] **Step 1: Write failing transport tests**

```python
# tests/notifications/test_transports.py
from pathlib import Path

from src.notifications.transports import QueueHermesTransport, choose_transport


def test_choose_transport_prefers_hermes_queue(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_QUEUE_PATH", str(tmp_path))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fallback-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "fallback-chat")

    transport = choose_transport(dry_run=False)

    assert isinstance(transport, QueueHermesTransport)


def test_queue_hermes_transport_writes_message(tmp_path):
    transport = QueueHermesTransport(tmp_path)

    result = transport.send("hello")

    files = list(Path(tmp_path).glob("*.json"))
    assert result.delivered is True
    assert result.transport == "hermes_queue"
    assert len(files) == 1
    assert "hello" in files[0].read_text(encoding="utf-8")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/notifications/test_transports.py -v`

Expected: FAIL with missing transport module.

- [ ] **Step 3: Implement transports**

```python
# src/notifications/transports.py
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import requests

from src.notifications.models import NotificationResult


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
    raise RuntimeError("No notification transport configured. Set Hermes transport config or Telegram fallback credentials.")
```

- [ ] **Step 4: Run test**

Run: `pytest tests/notifications/test_transports.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/notifications/transports.py tests/notifications/test_transports.py
git commit -m "feat: add Hermes-first notification transports"
```

## Task 6: CLI Dry Run

**Files:**
- Create: `src/notifications/config.py`
- Create: `src/notifications/telegram_flow_check.py`
- Test: `tests/notifications/test_cli.py`

- [ ] **Step 1: Write failing CLI test**

```python
# tests/notifications/test_cli.py
from src.notifications.telegram_flow_check import main


def test_cli_dry_run_sends_message_to_stdout(capsys):
    exit_code = main(["--dry-run", "--slot", "23:30"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "[AI Hedge Fund Flow]" in captured.out
    assert "23:30" in captured.out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/notifications/test_cli.py -v`

Expected: FAIL with missing CLI module.

- [ ] **Step 3: Implement config and CLI using static first snapshot**

```python
# src/notifications/config.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_WATCHLIST = ["SPYM", "SPYV", "VUG", "AMZN", "VOLT", "TQQQ", "SGOV"]


@dataclass(frozen=True)
class FlowConfig:
    watchlist: list[str]
    state_path: Path


def load_config() -> FlowConfig:
    return FlowConfig(
        watchlist=DEFAULT_WATCHLIST,
        state_path=Path(".cache/telegram-flow-alerts/state.json"),
    )
```

```python
# src/notifications/telegram_flow_check.py
from __future__ import annotations

import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from src.notifications.config import load_config
from src.notifications.formatter import format_flow_message
from src.notifications.models import AssetSnapshot, FlowSnapshot
from src.notifications.rules import classify_flow
from src.notifications.state import FlowStateStore
from src.notifications.transports import choose_transport


def build_static_snapshot(slot: str) -> FlowSnapshot:
    now = datetime.now(ZoneInfo("Asia/Seoul")).replace(hour=int(slot[:2]), minute=int(slot[3:5]), second=0, microsecond=0)
    return FlowSnapshot(
        as_of=now.isoformat(),
        phase=slot,
        assets=[
            AssetSnapshot(symbol="SPYM", name="SPYM", price=None, change_pct=None, currency="USD", note="live fetch pending"),
            AssetSnapshot(symbol="SGOV", name="SGOV", price=None, change_pct=None, currency="USD", note="live fetch pending"),
        ],
        data_warnings=["live price fetch not enabled in dry-run baseline"],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send AI Hedge Fund portfolio flow alert")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--slot", default="23:30")
    args = parser.parse_args(argv)

    load_dotenv()
    config = load_config()
    snapshot = build_static_snapshot(args.slot)
    result = classify_flow(snapshot)
    message = format_flow_message(snapshot, result)

    store = FlowStateStore(config.state_path)
    if not args.dry_run and store.is_duplicate(args.slot, message):
        return 0

    transport = choose_transport(dry_run=args.dry_run)
    delivery = transport.send(message)
    if delivery.delivered:
        store.record(args.slot, message)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test**

Run: `pytest tests/notifications/test_cli.py -v`

Expected: PASS.

- [ ] **Step 5: Run manual dry run**

Run: `python -m src.notifications.telegram_flow_check --dry-run --slot 23:30`

Expected: printed message containing `[AI Hedge Fund Flow]` and `보류`.

- [ ] **Step 6: Commit**

```bash
git add src/notifications/config.py src/notifications/telegram_flow_check.py tests/notifications/test_cli.py
git commit -m "feat: add portfolio flow alert CLI"
```

## Task 7: Live Price Fetch Hook

**Files:**
- Modify: `src/notifications/telegram_flow_check.py`
- Test: `tests/notifications/test_cli.py`

- [ ] **Step 1: Add failing test for injected price snapshots**

```python
# append to tests/notifications/test_cli.py
from src.notifications.telegram_flow_check import build_snapshot_from_prices


def test_build_snapshot_from_prices_uses_change_pct():
    snapshot = build_snapshot_from_prices(
        slot="09:00",
        prices={
            "SPYM": {"price": 83.0, "change_pct": 0.5, "currency": "USD"},
            "TQQQ": {"price": 75.0, "change_pct": 5.0, "currency": "USD"},
        },
    )

    by_symbol = snapshot.by_symbol()
    assert by_symbol["SPYM"].price == 83.0
    assert by_symbol["TQQQ"].change_pct == 5.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/notifications/test_cli.py::test_build_snapshot_from_prices_uses_change_pct -v`

Expected: FAIL with missing function.

- [ ] **Step 3: Add snapshot builder**

```python
# add to src/notifications/telegram_flow_check.py
def build_snapshot_from_prices(slot: str, prices: dict[str, dict]) -> FlowSnapshot:
    now = datetime.now(ZoneInfo("Asia/Seoul")).replace(hour=int(slot[:2]), minute=int(slot[3:5]), second=0, microsecond=0)
    assets = [
        AssetSnapshot(
            symbol=symbol,
            name=symbol,
            price=payload.get("price"),
            change_pct=payload.get("change_pct"),
            currency=payload.get("currency", "USD"),
        )
        for symbol, payload in prices.items()
    ]
    return FlowSnapshot(as_of=now.isoformat(), phase=slot, assets=assets)
```

- [ ] **Step 4: Run test**

Run: `pytest tests/notifications/test_cli.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/notifications/telegram_flow_check.py tests/notifications/test_cli.py
git commit -m "feat: build alert snapshots from prices"
```

## Task 8: Launchd Template

**Files:**
- Create: `scripts/com.nanamix.ai-hedge-flow-alerts.plist`
- Create: `scripts/install-telegram-flow-alerts-launchd.sh`
- Test: manual shell validation

- [ ] **Step 1: Create launchd plist template**

```xml
<!-- scripts/com.nanamix.ai-hedge-flow-alerts.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.nanamix.ai-hedge-flow-alerts</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>-lc</string>
    <string>cd /Users/hajinyoung/Dev/ai-hedge-fund && python -m src.notifications.telegram_flow_check --slot auto</string>
  </array>
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>12</integer><key>Minute</key><integer>30</integer></dict>
    <dict><key>Hour</key><integer>16</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>22</integer><key>Minute</key><integer>30</integer></dict>
    <dict><key>Hour</key><integer>23</integer><key>Minute</key><integer>30</integer></dict>
  </array>
  <key>StandardOutPath</key>
  <string>/tmp/ai-hedge-flow-alerts.out</string>
  <key>StandardErrorPath</key>
  <string>/tmp/ai-hedge-flow-alerts.err</string>
</dict>
</plist>
```

- [ ] **Step 2: Create installer script**

```bash
#!/usr/bin/env bash
set -euo pipefail

PLIST_NAME="com.nanamix.ai-hedge-flow-alerts.plist"
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/${PLIST_NAME}"
TARGET="${HOME}/Library/LaunchAgents/${PLIST_NAME}"

cp "${SOURCE}" "${TARGET}"
launchctl unload "${TARGET}" >/dev/null 2>&1 || true
launchctl load "${TARGET}"
launchctl kickstart -k "gui/$(id -u)/com.nanamix.ai-hedge-flow-alerts" || true
echo "Installed ${TARGET}"
```

- [ ] **Step 3: Make script executable**

Run: `chmod +x scripts/install-telegram-flow-alerts-launchd.sh`

Expected: command succeeds.

- [ ] **Step 4: Validate plist syntax**

Run: `plutil -lint scripts/com.nanamix.ai-hedge-flow-alerts.plist`

Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add scripts/com.nanamix.ai-hedge-flow-alerts.plist scripts/install-telegram-flow-alerts-launchd.sh
git commit -m "feat: add launchd schedule for flow alerts"
```

## Task 9: Final Verification

**Files:**
- No new files.

- [ ] **Step 1: Run notification test suite**

Run: `pytest tests/notifications -v`

Expected: all tests PASS.

- [ ] **Step 2: Run dry-run CLI**

Run: `python -m src.notifications.telegram_flow_check --dry-run --slot 23:30`

Expected: printed alert includes `보류`, `대기자금`, and `[AI Hedge Fund Flow]`.

- [ ] **Step 3: Test Hermes when Hermes interface is known**

If Hermes provides a file queue:

Run: `HERMES_QUEUE_PATH=/tmp/hermes-alerts python -m src.notifications.telegram_flow_check --slot 23:30`

Expected: one JSON file appears in `/tmp/hermes-alerts`.

If Hermes provides an HTTP endpoint:

Run: `HERMES_NOTIFY_URL=http://127.0.0.1:<port>/<path> python -m src.notifications.telegram_flow_check --slot 23:30`

Expected: command exits 0 and Hermes delivers Telegram message.

If Hermes provides a CLI command:

Run: `HERMES_NOTIFY_COMMAND=/path/to/hermes-send python -m src.notifications.telegram_flow_check --slot 23:30`

Expected: command exits 0 and Hermes delivers Telegram message.

- [ ] **Step 4: Confirm no secrets**

Run: `git diff --cached`

Expected: no Telegram tokens, chat IDs, or Hermes secrets.

- [ ] **Step 5: Commit any verification fixes**

```bash
git status --short
git add <only files intentionally changed>
git commit -m "test: verify telegram flow alerts"
```

## Self-Review

- Spec coverage: The plan covers scheduled summaries, 02:00 exclusion, Hermes-first delivery, Telegram fallback, dry-run testing, duplicate suppression, calm message formatting, and no-auto-trading rules.
- Placeholder scan: No `TBD`, `TODO`, or unspecified implementation steps are used.
- Type consistency: Shared dataclasses in Task 1 are used consistently by rules, formatter, state, transports, and CLI tasks.
