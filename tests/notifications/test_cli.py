from src.notifications.telegram_flow_check import build_snapshot_from_prices, main


def test_cli_dry_run_sends_message_to_stdout(capsys):
    exit_code = main(["--dry-run", "--slot", "23:30"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "[AI Hedge Fund Flow]" in captured.out
    assert "23:30" in captured.out


def test_cli_dry_run_does_not_write_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    exit_code = main(["--dry-run", "--slot", "23:30"])

    assert exit_code == 0
    assert not (tmp_path / ".cache/telegram-flow-alerts/state.json").exists()


def test_build_snapshot_from_prices_uses_change_pct():
    snapshot = build_snapshot_from_prices(
        slot="09:00",
        prices={
            "SPYM": {"price": 83.0, "change_pct": 0.5, "currency": "USD"},
            "TQQQ": {"price": 75.0, "change_pct": 5.0, "currency": "USD"},
        },
    )

    by_symbol = snapshot.by_symbol()
    assert by_symbol["SPYM"].price == 83.0
    assert by_symbol["TQQQ"].change_pct == 5.0


def test_cli_uses_live_prices_when_not_dry_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HERMES_QUEUE_PATH", str(tmp_path / "hermes-alerts"))
    monkeypatch.setattr(
        "src.notifications.telegram_flow_check.fetch_yahoo_prices",
        lambda symbols: type(
            "Result",
            (),
            {
                "prices": {"SPYM": {"price": 83.0, "change_pct": 0.4, "currency": "USD"}},
                "warnings": [],
            },
        )(),
    )

    exit_code = main(["--slot", "09:00"])

    assert exit_code == 0


def test_cli_live_prices_can_be_used_during_dry_run(capsys, monkeypatch):
    monkeypatch.setattr(
        "src.notifications.telegram_flow_check.fetch_yahoo_prices",
        lambda symbols: type(
            "Result",
            (),
            {
                "prices": {"SPYM": {"price": 83.0, "change_pct": 0.4, "currency": "USD"}},
                "warnings": [],
            },
        )(),
    )

    exit_code = main(["--dry-run", "--live-prices", "--slot", "09:00"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "SPYM" in captured.out
    assert "live price fetch not enabled" not in captured.out
