from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import requests


YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 ai-hedge-fund-flow-alerts/1.0",
    "Accept": "application/json",
}


@dataclass(frozen=True)
class PriceFetchResult:
    prices: dict[str, dict[str, float | str]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def fetch_yahoo_prices(symbols: list[str], session: Any | None = None, timeout: int = 10) -> PriceFetchResult:
    client = session or requests.Session()
    prices: dict[str, dict[str, float | str]] = {}
    warnings: list[str] = []

    for symbol in symbols:
        try:
            payload = _fetch_chart_payload(client, symbol, timeout)
            prices[symbol] = _parse_chart_payload(symbol, payload)
        except Exception as exc:
            warnings.append(f"{symbol}: price fetch failed ({exc})")

    return PriceFetchResult(prices=prices, warnings=warnings)


def _fetch_chart_payload(session: Any, symbol: str, timeout: int) -> dict:
    response = session.get(
        YAHOO_CHART_URL.format(symbol=symbol),
        timeout=timeout,
        params={"range": "2d", "interval": "1d"},
        headers=YAHOO_HEADERS,
    )
    if response.status_code >= 400:
        raise ValueError(f"HTTP {response.status_code}")
    return response.json()


def _parse_chart_payload(symbol: str, payload: dict) -> dict[str, float | str]:
    chart = payload.get("chart") or {}
    error = chart.get("error")
    if error:
        description = error.get("description") if isinstance(error, dict) else str(error)
        raise ValueError(description or "chart error")

    results = chart.get("result") or []
    if not results:
        raise ValueError("empty chart result")

    meta = results[0].get("meta") or {}
    price = _to_float(meta.get("regularMarketPrice"))
    previous_close = _to_float(meta.get("previousClose"))

    if price is None:
        raise ValueError("missing current price")

    if previous_close is None:
        previous_close = _previous_close_from_quotes(results[0])

    change_pct = None
    if previous_close and previous_close > 0:
        change_pct = ((price - previous_close) / previous_close) * 100

    return {
        "price": price,
        "change_pct": change_pct,
        "currency": meta.get("currency") or "USD",
    }


def _previous_close_from_quotes(result: dict) -> float | None:
    quotes = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    closes = [_to_float(value) for value in quotes.get("close", [])]
    closes = [value for value in closes if value is not None]
    if len(closes) < 2:
        return None
    return closes[-2]


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
