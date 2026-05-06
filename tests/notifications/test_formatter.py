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
