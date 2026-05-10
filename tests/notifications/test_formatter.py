from src.notifications.formatter import format_flow_message
from src.notifications.models import AssetSnapshot, CashEvent, ExternalSignal, FlowSnapshot, RuleResult


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
        urgent=True,
    )

    message = format_flow_message(snapshot, result)

    assert "[긴급]" in message
    assert "[AI Hedge Fund Flow]" in message
    assert "23:30" in message
    assert "보류" in message
    assert "TQQQ" in message
    assert "레버리지" in message
    assert len(message) < 1200


def test_format_flow_message_includes_planned_cash_event():
    snapshot = FlowSnapshot(
        as_of="2026-05-10T23:00:00+09:00",
        phase="pre_deposit",
        assets=[],
        cash_events=[
            CashEvent(
                date="2026-05-11",
                broker="Toss Securities",
                amount=2_000_000,
                currency="KRW",
                status="planned",
                note="추가입금 예정",
            )
        ],
    )
    result = RuleResult(
        label="대기",
        summary="입금 예정 자금은 대기자금으로 분류합니다.",
        risk_signals=["Toss Securities 2026-05-11: 2,000,000 KRW 입금 예정"],
        actions=["입금 확인 전 신규 매수 금지"],
    )

    message = format_flow_message(snapshot, result)

    assert "입금/현금 이벤트" in message
    assert "Toss Securities" in message
    assert "2,000,000 KRW" in message


def test_format_flow_message_includes_external_opinions():
    snapshot = FlowSnapshot(
        as_of="2026-05-10T21:30:00+09:00",
        phase="us_open",
        assets=[],
        external_signals=[
            ExternalSignal(
                source="HKUDS/AI-Trader",
                as_of="2026-05-10T21:30:00+09:00",
                symbol="SPYM",
                action="review",
                confidence=0.62,
                horizon="days",
                rationale="Core rebuild candidate, not an immediate buy.",
                risk_notes=["Do not chase after sharp rises."],
                raw_action="buy",
            )
        ],
    )
    result = RuleResult(
        label="대기",
        summary="큰 변동 신호가 없어 기존 계획을 유지합니다.",
        risk_signals=["레버리지 재진입 금지 유지"],
        actions=["신규 매수: 없음"],
    )

    message = format_flow_message(snapshot, result)

    assert "외부 의견" in message
    assert "HKUDS/AI-Trader" in message
    assert "SPYM" in message
    assert "review" in message
    assert "Core rebuild candidate" in message
