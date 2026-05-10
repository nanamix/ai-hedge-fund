from __future__ import annotations

from datetime import datetime
from typing import Any

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


def build_flow_payload(snapshot: FlowSnapshot, result: RuleResult) -> dict[str, Any]:
    major_changes = [
        _asset_line(asset.symbol, asset.price, asset.change_pct, asset.currency)
        for asset in snapshot.assets[:8]
    ]
    if not major_changes:
        major_changes = ["- 가격 데이터 없음"]
    cash_lines = [
        f"- {event.broker}: {event.date}, {event.display_amount()}, {event.status}"
        + (f" ({event.note})" if event.note else "")
        for event in snapshot.cash_events
    ]
    external_opinion_lines = [_external_signal_line(signal) for signal in snapshot.external_signals[:5]]

    slot_label = snapshot.phase if snapshot.phase else "auto"
    next_check = "다음 체크까지 관망" if slot_label == "auto" else f"다음 체크 슬롯: {slot_label}"
    body = (
        f"판단: {result.label}\n"
        f"기준 시각: {_display_time(snapshot.as_of)}"
    )

    return {
        "target": "telegram",
        "kind": "urgent" if result.urgent else "summary",
        "title": f"[AI Hedge Fund Flow] {_display_time(snapshot.as_of)}",
        "summary": result.summary,
        "body": body,
        "bullets": major_changes,
        "cash_events": cash_lines,
        "external_opinions": external_opinion_lines,
        "risks": result.risk_signals[:5],
        "actions": [*result.actions[:5], next_check],
        "decision": result.label,
        "slot": slot_label,
        "source": "ai-hedge-fund",
        "priority": "high" if result.urgent else "normal",
        "created_at": snapshot.as_of,
    }



def format_flow_message(snapshot: FlowSnapshot, result: RuleResult) -> str:
    payload = build_flow_payload(snapshot, result)
    prefix = "[긴급] " if result.urgent else ""
    lines = [
        f"{prefix}{payload['title']}",
        "",
        f"요약: {payload['summary']}",
        f"판단: {payload['decision']}",
        "",
        "주요 변화",
    ]

    lines.extend(payload["bullets"])
    if payload["cash_events"]:
        lines.extend(["", "입금/현금 이벤트"])
        lines.extend(payload["cash_events"])
    if payload["external_opinions"]:
        lines.extend(["", "외부 의견"])
        lines.extend(payload["external_opinions"])
    lines.extend(["", "리스크 신호"])
    lines.extend(f"- {signal}" for signal in payload["risks"])
    lines.extend(["", "오늘 행동"])
    lines.extend(f"- {action}" for action in payload["actions"][:5])

    return "\n".join(lines)


def _external_signal_line(signal) -> str:
    confidence = "n/a" if signal.confidence is None else f"{signal.confidence:.2f}"
    rationale = f" - {signal.rationale}" if signal.rationale else ""
    return f"- {signal.source} {signal.symbol}: {signal.action}, confidence {confidence}{rationale}"
