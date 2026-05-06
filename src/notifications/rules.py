from __future__ import annotations

from src.notifications.models import FlowSnapshot, RuleResult


CORE_SYMBOLS = {"SPY", "SPYM", "SPYV", "SGOV", "BIL", "TFLO"}
GROWTH_OR_THEME_SYMBOLS = {"VUG", "AMZN", "VOLT", "TQQQ"}


def classify_flow(snapshot: FlowSnapshot) -> RuleResult:
    risk_signals: list[str] = []
    actions: list[str] = []
    urgent = False

    if snapshot.data_warnings:
        return RuleResult(
            label="보류",
            summary="데이터가 충분하지 않아 신규 매수 판단은 보류합니다.",
            risk_signals=[f"데이터 경고: {warning}" for warning in snapshot.data_warnings],
            actions=["신규 매수: 보류", "대기자금: 유지", "다음 체크까지 관망"],
            urgent=True,
        )

    for asset in snapshot.assets:
        change = asset.change_pct
        if change is None:
            risk_signals.append(f"{asset.symbol}: 변동률 데이터 없음")
            continue

        if asset.symbol == "TQQQ" and change > 0:
            urgent = True
            risk_signals.append("TQQQ 상승은 레버리지 재진입 신호가 아니라 추격매수 경고입니다.")
            actions.append("TQQQ: 신규매수 금지 유지")

        if asset.symbol in CORE_SYMBOLS and abs(change) >= 2.0:
            risk_signals.append(f"{asset.symbol}: 코어/대기자금 자산 변동 {change:.2f}%")

        if asset.symbol in GROWTH_OR_THEME_SYMBOLS and abs(change) >= 4.0:
            urgent = True
            risk_signals.append(f"{asset.symbol}: 성장/테마 자산 변동 {change:.2f}%")

    if risk_signals:
        return RuleResult(
            label="보류",
            summary="변동성이 커서 계획 없는 신규 매수는 보류합니다.",
            risk_signals=risk_signals,
            actions=actions or ["신규 매수: 보류", "대기자금: 유지"],
            urgent=urgent,
        )

    return RuleResult(
        label="대기",
        summary="큰 변동 신호가 없어 기존 계획을 유지합니다.",
        risk_signals=["레버리지 재진입 금지 유지", "추격매수 방지 규칙 유지"],
        actions=["신규 매수: 없음", "대기자금: 유지"],
    )
