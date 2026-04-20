import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from hermes_pulse.models import CollectedItem, Provenance


class LocationContextConnector:
    id = "location_context"
    source_family = "location"

    def __init__(self, runner: Callable[[], dict[str, Any]] | None = None) -> None:
        self._runner = runner or (lambda: {})

    def collect(self) -> list[CollectedItem]:
        payload = self._runner()
        place = payload.get("place") or "Unknown place"
        maps_url = payload.get("maps_url")
        context = payload.get("context") or []
        detected_reason = payload.get("detected_reason") or _infer_detected_reason(payload)
        body = "\n".join(f"- {value}" for value in context)
        return [
            CollectedItem(
                id=f"location_context:{place}",
                source="location_context",
                source_kind="place",
                title=place,
                body=body,
                url=maps_url,
                provenance=Provenance(
                    provider="location_context",
                    acquisition_mode="local_store",
                    raw_record_id=str(payload.get("arrived_at") or place),
                ),
                metadata={
                    "arrived_at": payload.get("arrived_at"),
                    "context": context,
                    "maps_url": maps_url,
                    "local_time": payload.get("local_time"),
                    "dwell_minutes": payload.get("dwell_minutes"),
                    "place_category": payload.get("place_category"),
                    "detected_reason": detected_reason,
                },
            )
        ]


def _infer_detected_reason(payload: dict[str, Any]) -> str:
    local_time = payload.get("local_time")
    dwell_minutes = payload.get("dwell_minutes") or 0
    if dwell_minutes and dwell_minutes < 15:
        return "transient_stop"
    hour = _extract_hour(local_time)
    if hour is None:
        return "stopped_moving"
    if 11 <= hour < 14 or 17 <= hour < 20:
        return "meal_window"
    if 14 <= hour < 17:
        return "snack_window"
    return "stopped_moving"


def _extract_hour(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).hour
    except ValueError:
        return None


def load_location_context_fixture(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text())
