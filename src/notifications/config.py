from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path

from src.notifications.models import CashEvent


DEFAULT_WATCHLIST = ["SPYM", "SPYV", "VUG", "AMZN", "VOLT", "TQQQ", "SGOV"]
DEFAULT_CASH_EVENTS_PATH = Path(".cache/telegram-flow-alerts/cash-events.json")
DEFAULT_EXTERNAL_SIGNALS_PATH = Path(".cache/telegram-flow-alerts/external-signals.json")


@dataclass(frozen=True)
class FlowConfig:
    watchlist: list[str]
    state_path: Path
    cash_events_path: Path
    external_signals_path: Path


def load_config() -> FlowConfig:
    watchlist = _env_list("AI_HEDGE_FLOW_WATCHLIST") or DEFAULT_WATCHLIST
    state_path = Path(os.getenv("AI_HEDGE_FLOW_STATE_PATH", ".cache/telegram-flow-alerts/state.json"))
    cash_events_path = Path(os.getenv("AI_HEDGE_FLOW_CASH_EVENTS_PATH", str(DEFAULT_CASH_EVENTS_PATH)))
    external_signals_path = Path(os.getenv("AI_HEDGE_FLOW_EXTERNAL_SIGNALS_PATH", str(DEFAULT_EXTERNAL_SIGNALS_PATH)))
    return FlowConfig(
        watchlist=watchlist,
        state_path=state_path,
        cash_events_path=cash_events_path,
        external_signals_path=external_signals_path,
    )


def _env_list(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [item.strip().upper() for item in raw.split(",") if item.strip()]


def load_cash_events(path: str | Path) -> list[CashEvent]:
    event_path = Path(path)
    if not event_path.exists():
        return []

    raw_events = json.loads(event_path.read_text(encoding="utf-8"))
    return [
        CashEvent(
            date=str(event["date"]),
            broker=str(event.get("broker", "")),
            amount=float(event["amount"]),
            currency=str(event.get("currency", "KRW")).upper(),
            status=str(event.get("status", "planned")),
            note=str(event.get("note", "")),
        )
        for event in raw_events
    ]
