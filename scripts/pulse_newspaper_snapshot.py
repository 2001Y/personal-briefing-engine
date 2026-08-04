#!/usr/bin/env python3
"""Persist one completed date-level Pulse output as an immutable slot snapshot."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from hermes_pulse.visual_newspaper import REQUIRED_SLOTS, snapshot_pulse_slot  # noqa: E402

TZ = ZoneInfo("Asia/Tokyo")
DEFAULT_ARCHIVE_ROOT = Path.home() / "Pulse" / "HermesPulseMorning"
DEFAULT_SLOT_ROOT = Path.home() / "Pulse" / "HermesPulseMorningSlots"


def _slot_for_hour(hour: int) -> str:
    if 6 <= hour < 12:
        return "morning"
    if 12 <= hour < 18:
        return "afternoon"
    if 18 <= hour <= 23 or 0 <= hour < 6:
        return "evening"
    raise ValueError(f"cannot infer Pulse slot from hour={hour}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive-root", type=Path, default=DEFAULT_ARCHIVE_ROOT)
    parser.add_argument("--slot-root", type=Path, default=DEFAULT_SLOT_ROOT)
    parser.add_argument("--local-date")
    parser.add_argument("--slot", choices=REQUIRED_SLOTS)
    args = parser.parse_args(argv)

    now = datetime.now(TZ)
    local_date = args.local_date or now.date().isoformat()
    slot = args.slot or _slot_for_hour(now.hour)
    source = args.archive_root / local_date
    snapshot = snapshot_pulse_slot(
        source,
        args.slot_root,
        local_date=local_date,
        slot=slot,
    )
    print(f"snapshot={snapshot}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
