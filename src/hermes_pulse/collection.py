from collections.abc import Mapping
from typing import Any

from hermes_pulse.models import TriggerEvent, TriggerProfile


COLLECTION_PRESETS = {
    "broad_day_start": [
        "feed_registry",
        "known_source_search",
        "x_signals",
        "google_calendar",
        "gmail",
        "hermes_history",
        "notes",
    ],
    "broad_day_end": [
        "feed_registry",
        "known_source_search",
        "x_signals",
        "google_calendar",
        "gmail",
        "hermes_history",
        "notes",
    ],
    "calendar_leave_now": ["google_calendar"],
}


def collect_for_trigger(
    trigger: TriggerEvent,
    profile: TriggerProfile,
    connectors: Mapping[str, Any],
) -> list[Any]:
    collected: list[Any] = []
    for connector_id in COLLECTION_PRESETS.get(profile.collection_preset, []):
        connector = connectors.get(connector_id)
        if connector is None:
            continue
        collected.extend(connector.collect())
    return collected
