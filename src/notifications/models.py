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
class CashEvent:
    date: str
    broker: str
    amount: float
    currency: str
    status: str
    note: str = ""

    def display_amount(self) -> str:
        return f"{self.amount:,.0f} {self.currency}"


@dataclass(frozen=True)
class FlowSnapshot:
    as_of: str
    phase: str
    assets: list[AssetSnapshot] = field(default_factory=list)
    data_warnings: list[str] = field(default_factory=list)
    cash_events: list[CashEvent] = field(default_factory=list)

    def by_symbol(self) -> dict[str, AssetSnapshot]:
        return {asset.symbol: asset for asset in self.assets}


@dataclass(frozen=True)
class RuleResult:
    label: ActionLabel
    summary: str
    risk_signals: list[str]
    actions: list[str]
    urgent: bool = False


@dataclass(frozen=True)
class NotificationResult:
    transport: str
    delivered: bool
    detail: str
