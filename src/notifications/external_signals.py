from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.notifications.models import ExternalSignal


BUY_LIKE_ACTIONS = {"buy", "strong_buy", "accumulate"}
SELL_LIKE_ACTIONS = {"sell", "reduce"}
HOLD_LIKE_ACTIONS = {"hold"}
WATCH_LIKE_ACTIONS = {"watch", "review"}
DISALLOWED_ACTIONS = {"short", "cover"}


def normalize_external_signal(raw: dict) -> ExternalSignal:
    raw_action = str(raw.get("raw_action") or raw.get("action") or "").strip().lower()
    risk_notes = [str(note) for note in raw.get("risk_notes", [])]

    action = _safe_action(raw_action)
    if action == "avoid":
        risk_notes = ["금지 신호: short/cover/leveraged action은 채택하지 않음", *risk_notes]

    return ExternalSignal(
        source=str(raw.get("source", "external")),
        as_of=str(raw.get("as_of", "")),
        symbol=str(raw.get("symbol", "")).upper(),
        action=action,
        confidence=_optional_float(raw.get("confidence")),
        horizon=str(raw.get("horizon", "")),
        rationale=str(raw.get("rationale", "")),
        risk_notes=risk_notes,
        raw_action=raw_action,
    )


def load_external_signals(
    path: str | Path,
    now: str | None = None,
    max_age_hours: int = 24,
) -> list[ExternalSignal]:
    signal_path = Path(path)
    if not signal_path.exists():
        return []

    raw_signals = json.loads(signal_path.read_text(encoding="utf-8"))
    current = _parse_dt(now) if now else datetime.now(ZoneInfo("Asia/Seoul"))

    signals = []
    for raw in raw_signals:
        signal = normalize_external_signal(raw)
        if _is_fresh(signal.as_of, current=current, max_age_hours=max_age_hours):
            signals.append(signal)
    return signals


def _safe_action(raw_action: str) -> str:
    if raw_action in BUY_LIKE_ACTIONS or raw_action in SELL_LIKE_ACTIONS:
        return "review"
    if raw_action in HOLD_LIKE_ACTIONS:
        return "hold"
    if raw_action in WATCH_LIKE_ACTIONS:
        return raw_action
    if raw_action in DISALLOWED_ACTIONS or "lever" in raw_action:
        return "avoid"
    return "watch"


def _is_fresh(as_of: str, current: datetime, max_age_hours: int) -> bool:
    parsed = _parse_dt(as_of)
    if parsed is None:
        return False
    age_seconds = (current - parsed).total_seconds()
    return 0 <= age_seconds <= max_age_hours * 60 * 60


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=ZoneInfo("Asia/Seoul"))
    return parsed


def _optional_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
