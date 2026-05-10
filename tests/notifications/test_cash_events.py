import json

from src.notifications.config import load_cash_events


def test_load_cash_events_reads_json_file(tmp_path):
    path = tmp_path / "cash-events.json"
    path.write_text(
        json.dumps(
            [
                {
                    "date": "2026-05-11",
                    "broker": "Toss Securities",
                    "amount": 2000000,
                    "currency": "KRW",
                    "status": "planned",
                    "note": "추가입금 예정",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    events = load_cash_events(path)

    assert len(events) == 1
    assert events[0].amount == 2_000_000
    assert events[0].broker == "Toss Securities"


def test_load_cash_events_returns_empty_for_missing_file(tmp_path):
    assert load_cash_events(tmp_path / "missing.json") == []
