from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


DEFAULT_WATCHLIST = ["SPYM", "SPYV", "VUG", "AMZN", "VOLT", "TQQQ", "SGOV"]


@dataclass(frozen=True)
class FlowConfig:
    watchlist: list[str]
    state_path: Path


def load_config() -> FlowConfig:
    watchlist = _env_list("AI_HEDGE_FLOW_WATCHLIST") or DEFAULT_WATCHLIST
    state_path = Path(os.getenv("AI_HEDGE_FLOW_STATE_PATH", ".cache/telegram-flow-alerts/state.json"))
    return FlowConfig(
        watchlist=watchlist,
        state_path=state_path,
    )


def _env_list(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [item.strip().upper() for item in raw.split(",") if item.strip()]
