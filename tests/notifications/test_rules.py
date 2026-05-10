from src.notifications.models import AssetSnapshot, CashEvent, FlowSnapshot
from src.notifications.rules import classify_flow


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


def test_classify_defaults_to_hold_when_data_missing():
    snapshot = FlowSnapshot(
        as_of="2026-05-06T23:30:00+09:00",
        phase="us_open",
        assets=[],
        data_warnings=["price data unavailable"],
    )

    result = classify_flow(snapshot)

    assert result.label == "보류"
    assert result.urgent is True
    assert "데이터" in result.summary
    assert any("매수 금지" in action or "보류" in action for action in result.actions)


def test_classify_warns_against_tqqq_fomo_as_urgent():
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
    assert result.urgent is True
    assert any("레버리지" in signal for signal in result.risk_signals)
    assert any("TQQQ" in action for action in result.actions)


def test_classify_treats_planned_cash_deposit_as_waiting_capital():
    snapshot = FlowSnapshot(
        as_of="2026-05-10T23:00:00+09:00",
        phase="pre_deposit",
        assets=[
            AssetSnapshot(symbol="SGOV", name="SGOV", price=100.44, change_pct=0.0, currency="USD"),
        ],
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

    result = classify_flow(snapshot)

    assert result.label == "대기"
    assert result.urgent is False
    assert any("2,000,000 KRW" in signal for signal in result.risk_signals)
    assert any("입금 확인 전" in action for action in result.actions)
