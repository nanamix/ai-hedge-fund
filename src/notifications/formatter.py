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
    prefix = "[긴급] " if result.urgent else ""
    lines = [
        f"{prefix}[AI Hedge Fund Flow] {_display_time(snapshot.as_of)}",
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
