from src.notifications.telegram_flow_check import build_snapshot_from_prices, main
import json


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


def test_cli_dry_run_includes_external_signals(tmp_path, capsys, monkeypatch):
    signal_path = tmp_path / "external-signals.json"
    signal_path.write_text(
        json.dumps(
            [
                {
                    "source": "HKUDS/AI-Trader",
                    "as_of": "2026-05-10T21:30:00+09:00",
                    "symbol": "SPYM",
                    "raw_action": "buy",
                    "confidence": 0.62,
                    "rationale": "Core rebuild candidate",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_HEDGE_FLOW_EXTERNAL_SIGNALS_PATH", str(signal_path))

    exit_code = main(["--dry-run", "--slot", "09:00"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "외부 의견" in captured.out
    assert "HKUDS/AI-Trader" in captured.out
    assert "review" in captured.out
