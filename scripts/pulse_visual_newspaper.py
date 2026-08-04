#!/usr/bin/env python3
"""Generate and deliver the previous day's Pulse visual newspaper.

The normal cron path is intentionally silent on success because this script
posts the Slack root itself. stdout is reserved for --dry-run diagnostics;
errors go to stderr and return non-zero so Hermes reports the failure.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from collections.abc import Callable
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[1]
SLACK_DIRECT_PATH = Path.home() / ".hermes" / "scripts" / "slack_direct.py"
sys.path.insert(0, str(REPO_ROOT / "src"))

from hermes_pulse.visual_newspaper import (  # noqa: E402
    DEFAULT_CHROME_PATH,
    DEFAULT_TIMEZONE,
    create_newspaper_artifacts,
    load_previous_day_slots,
    post_newspaper_files,
)

TZ = ZoneInfo(DEFAULT_TIMEZONE)
DEFAULT_SLOT_ROOT = Path.home() / "Pulse" / "HermesPulseMorningSlots"
DEFAULT_OUTPUT_ROOT = Path.home() / "Pulse" / "HermesPulseNewspaper"
DEFAULT_CHANNEL = "D0AT8A3RB9A"


def _load_slack_direct() -> Callable[..., dict[str, Any]]:
    spec = importlib.util.spec_from_file_location("hermes_pulse_newspaper_slack", SLACK_DIRECT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load Slack uploader: {SLACK_DIRECT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    uploader = getattr(module, "upload_files", None)
    if not callable(uploader):
        raise RuntimeError("Slack uploader does not expose upload_files")
    return cast(Callable[..., dict[str, Any]], uploader)


def _target_date(value: str | None) -> date:
    if value:
        return date.fromisoformat(value)
    return datetime.now(TZ).date() - timedelta(days=1)


def _read_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _write_delivery_receipt(manifest_path: Path, result: dict[str, Any], channel: str) -> None:
    manifest = _read_manifest(manifest_path)
    response = {
        key: result[key]
        for key in ("ok", "channel", "ts", "message_id", "files")
        if key in result
    }
    manifest["delivery"] = {
        "status": "ok",
        "platform": "slack",
        "channel": os.environ.get("SLACK_HOME_CHANNEL", DEFAULT_CHANNEL),
        "response": response,
        "delivered_at": datetime.now(TZ).isoformat(),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot-root", type=Path, default=DEFAULT_SLOT_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--target-date")
    parser.add_argument("--channel", default=os.environ.get("SLACK_HOME_CHANNEL", DEFAULT_CHANNEL))
    parser.add_argument("--chrome-path", type=Path, default=DEFAULT_CHROME_PATH)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    target_date = _target_date(args.target_date)
    output_directory = args.output_root / target_date.isoformat()
    existing_manifest = _read_manifest(output_directory / "manifest.json")
    if not args.force and existing_manifest.get("delivery", {}).get("status") == "ok":
        if args.dry_run:
            print(json.dumps({"status": "already-delivered", "directory": str(output_directory)}))
        return 0

    snapshots = load_previous_day_slots(args.slot_root, target_date)
    artifacts = create_newspaper_artifacts(
        snapshots,
        target_date,
        args.output_root,
        chrome_path=args.chrome_path,
    )
    upload_paths = [artifacts["cover_gif"], *artifacts["pages"][1:]]
    payload = {
        "target_date": target_date.isoformat(),
        "directory": str(artifacts["directory"]),
        "html": str(artifacts["html"]),
        "pdf": str(artifacts["pdf"]),
        "pages": [str(path) for path in artifacts["pages"]],
        "upload_paths": [str(path) for path in upload_paths],
    }
    if args.dry_run:
        print(json.dumps({"status": "rendered", **payload}, ensure_ascii=False))
        return 0

    result = post_newspaper_files(
        upload_paths,
        channel=args.channel,
        uploader=_load_slack_direct(),
    )
    _write_delivery_receipt(artifacts["manifest"], result, args.channel)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"pulse visual newspaper failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
