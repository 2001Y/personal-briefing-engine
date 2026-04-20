import json
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from hermes_pulse.models import CitationLink, CollectedItem, ItemTimestamps, Provenance


class GoogleCalendarConnector:
    id = "google_calendar"
    source_family = "calendar"

    def __init__(self, runner: Callable[[], list[dict[str, Any]]] | None = None) -> None:
        self._runner = runner or _run_google_calendar_list

    def collect(self) -> list[CollectedItem]:
        return [_normalize_event(record) for record in self._runner()]


def _normalize_event(record: dict[str, Any]) -> CollectedItem:
    event_id = record["id"]
    url = record.get("htmlLink")
    attendees = [_normalize_attendee(value) for value in record.get("attendees") or []]
    title = record.get("summary") or "Calendar event"
    return CollectedItem(
        id=f"google_calendar:{event_id}",
        source="google_calendar",
        source_kind="event",
        title=title,
        excerpt=record.get("description"),
        body=record.get("description"),
        url=url,
        people=[value for value in attendees if value],
        place_refs=[record["location"]] if record.get("location") else [],
        timestamps=ItemTimestamps(start_at=record.get("start"), end_at=record.get("end")),
        provenance=Provenance(
            provider="google_calendar",
            acquisition_mode="official_api",
            authority_tier="primary",
            primary_source_url=url,
            raw_record_id=event_id,
        ),
        citation_chain=[CitationLink(label=title, url=url, relation="primary")] if url else [],
        metadata={"future_relevance": True, "location": record.get("location"), "travel_minutes": record.get("travel_minutes")},
    )


def _normalize_attendee(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("email") or value.get("displayName")
    return None


def _run_google_calendar_list() -> list[dict[str, Any]]:
    script = os.environ.get(
        "GOOGLE_WORKSPACE_API_SCRIPT",
        str(Path.home() / ".hermes" / "skills" / "productivity" / "google-workspace" / "scripts" / "google_api.py"),
    )
    result = subprocess.run(
        ["python3", script, "calendar", "list"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    if not isinstance(payload, list):
        raise ValueError("Google Calendar API payload must be a list")
    return payload
