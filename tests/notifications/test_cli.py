from src.notifications.telegram_flow_check import main


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
