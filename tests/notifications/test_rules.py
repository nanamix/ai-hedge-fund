from src.notifications.models import AssetSnapshot, FlowSnapshot


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
