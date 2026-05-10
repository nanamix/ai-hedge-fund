import json

from src.notifications.external_signals import load_external_signals, normalize_external_signal


def test_normalize_buy_like_signal_to_review():
    signal = normalize_external_signal(
        {
            "source": "HKUDS/AI-Trader",
            "as_of": "2026-05-10T21:30:00+09:00",
            "symbol": "SPYM",
            "raw_action": "buy",
            "confidence": 0.62,
            "rationale": "Core rebuild candidate",
        }
    )

    assert signal.action == "review"
    assert signal.raw_action == "buy"
    assert signal.source == "HKUDS/AI-Trader"


def test_normalize_short_and_cover_to_avoid():
    short_signal = normalize_external_signal(
        {
            "source": "HKUDS/AI-Trader",
            "as_of": "2026-05-10T21:30:00+09:00",
            "symbol": "AMZN",
            "raw_action": "short",
            "rationale": "Momentum fading",
        }
    )
    cover_signal = normalize_external_signal(
        {
            "source": "HKUDS/AI-Trader",
            "as_of": "2026-05-10T21:30:00+09:00",
            "symbol": "TQQQ",
            "raw_action": "cover",
            "rationale": "Close short",
        }
    )

    assert short_signal.action == "avoid"
    assert cover_signal.action == "avoid"
    assert "금지" in short_signal.risk_notes[0]


def test_load_external_signals_filters_stale_items(tmp_path):
    path = tmp_path / "external-signals.json"
    path.write_text(
        json.dumps(
            [
                {
                    "source": "HKUDS/AI-Trader",
                    "as_of": "2026-05-10T21:30:00+09:00",
                    "symbol": "SPYM",
                    "raw_action": "buy",
                    "rationale": "Fresh",
                },
                {
                    "source": "HKUDS/AI-Trader",
                    "as_of": "2026-05-08T21:30:00+09:00",
                    "symbol": "VUG",
                    "raw_action": "buy",
                    "rationale": "Stale",
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    signals = load_external_signals(path, now="2026-05-10T22:00:00+09:00", max_age_hours=24)

    assert [signal.symbol for signal in signals] == ["SPYM"]


def test_load_external_signals_returns_empty_for_missing_file(tmp_path):
    assert load_external_signals(tmp_path / "missing.json") == []
