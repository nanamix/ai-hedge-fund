from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_WATCHLIST = ["SPYM", "SPYV", "VUG", "AMZN", "VOLT", "TQQQ", "SGOV"]


@dataclass(frozen=True)
class FlowConfig:
    watchlist: list[str]
    state_path: Path


def load_config() -> FlowConfig:
    return FlowConfig(
        watchlist=DEFAULT_WATCHLIST,
        state_path=Path(".cache/telegram-flow-alerts/state.json"),
    )
