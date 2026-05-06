from __future__ import annotations

import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from src.notifications.config import load_config
from src.notifications.formatter import format_flow_message
from src.notifications.models import AssetSnapshot, FlowSnapshot
from src.notifications.rules import classify_flow
from src.notifications.state import FlowStateStore
from src.notifications.transports import choose_transport


def _slot_time(slot: str) -> tuple[int, int]:
    if slot == "auto":
        now = datetime.now(ZoneInfo("Asia/Seoul"))
        return now.hour, now.minute
    hour, minute = slot.split(":", 1)
    return int(hour), int(minute)


def build_static_snapshot(slot: str) -> FlowSnapshot:
    hour, minute = _slot_time(slot)
    now = datetime.now(ZoneInfo("Asia/Seoul")).replace(hour=hour, minute=minute, second=0, microsecond=0)
    return FlowSnapshot(
        as_of=now.isoformat(),
        phase=slot,
        assets=[
            AssetSnapshot(symbol="SPYM", name="SPYM", price=None, change_pct=None, currency="USD", note="live fetch pending"),
            AssetSnapshot(symbol="SGOV", name="SGOV", price=None, change_pct=None, currency="USD", note="live fetch pending"),
        ],
        data_warnings=["live price fetch not enabled in dry-run baseline"],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send AI Hedge Fund portfolio flow alert")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--slot", default="23:30")
    args = parser.parse_args(argv)

    load_dotenv()
    config = load_config()
    snapshot = build_static_snapshot(args.slot)
    result = classify_flow(snapshot)
    message = format_flow_message(snapshot, result)

    store = FlowStateStore(config.state_path)
    if not args.dry_run and store.is_duplicate(args.slot, message):
        return 0

    transport = choose_transport(dry_run=args.dry_run)
    delivery = transport.send(message)
    if delivery.delivered:
        if not args.dry_run:
            store.record(args.slot, message)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
