from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from html import unescape
import re

from hermes_pulse.models import Candidate, CitationLink, CollectedItem
from hermes_pulse.synthesis import bundle_candidates_into_sections


SECTION_TITLES = {
    "today": "Today",
    "incoming": "Incoming",
    "followup": "Followup",
    "resurface": "Resurface",
    "feed_updates": "Feed updates",
}
REQUIRED_SECTIONS = ("today", "incoming", "followup", "resurface")
SECTION_ITEM_LIMITS = {
    "today": 3,
    "incoming": 3,
    "followup": 3,
    "resurface": 3,
    "feed_updates": 3,
}
HTML_TAG_RE = re.compile(r"<[^>]+>")


def render_morning_digest(
    candidates: Iterable[Candidate],
    items: Iterable[CollectedItem],
) -> str:
    items_by_id = {item.id: item for item in items}
    sections = bundle_candidates_into_sections(candidates)

    lines = ["# Morning Digest", ""]
    for section_name in REQUIRED_SECTIONS:
        lines.extend(_render_section(section_name, sections.get(section_name, []), items_by_id))

    feed_updates = sections.get("feed_updates", [])
    if feed_updates:
        lines.extend(_render_section("feed_updates", feed_updates, items_by_id))

    return "\n".join(lines).rstrip() + "\n"


def render_leave_now_warning(items: Iterable[CollectedItem], *, now: datetime) -> str | None:
    candidate = _find_leave_now_candidate(items, now)
    if candidate is None:
        return None

    item, departure_at, travel_minutes = candidate
    start_at = item.timestamps.start_at if item.timestamps is not None else None
    lines = [
        "# Leave now",
        "",
        f"- Event: {item.title or item.id}",
        f"- Starts at: {start_at}",
        f"- Location: {item.metadata.get('location') or 'Unknown'}",
        f"- Travel estimate: {travel_minutes} min",
        f"- Recommended departure: {_format_timestamp(departure_at)}",
    ]
    if item.url:
        lines.append(f"- Event URL: {item.url}")
    return "\n".join(lines).rstrip() + "\n"


def render_mail_operational_warning(items: Iterable[CollectedItem]) -> str | None:
    item = next((value for value in items if value.source == "gmail" and value.intent_signals and value.intent_signals.unread), None)
    if item is None:
        return None
    lines = [
        "# Operational mail",
        "",
        f"- Subject: {item.title or item.id}",
        f"- From: {item.people[0] if item.people else 'Unknown'}",
    ]
    summary = _single_line(item.excerpt) or _single_line(item.body)
    if summary:
        lines.append(f"- Summary: {summary}")
    if item.url:
        lines.append(f"- Mail URL: {item.url}")
    return "\n".join(lines).rstrip() + "\n"


def render_shopping_replenishment_action_prep(items: Iterable[CollectedItem]) -> str | None:
    item = next(iter(items), None)
    if item is None:
        return None
    fields = _parse_key_value_lines(item.body or "")
    lines = [
        "# Shopping action prep",
        "",
        f"- Item: {fields.get('buy') or item.title or item.id}",
    ]
    if fields.get("why"):
        lines.append(f"- Why: {fields['why']}")
    if fields.get("preferred store"):
        lines.append(f"- Preferred store: {fields['preferred store']}")
    if fields.get("link"):
        lines.append(f"- Link: {fields['link']}")
    return "\n".join(lines).rstrip() + "\n"


def render_feed_update_nudge(items: Iterable[CollectedItem]) -> str | None:
    feed_items = [item for item in items if item.source_kind == "feed_item"]
    if not feed_items:
        return None
    feed_items.sort(key=lambda item: (0 if item.provenance and item.provenance.authority_tier == "primary" else 1, item.id))
    item = feed_items[0]
    lines = [
        "# Feed update",
        "",
        f"- Source: {item.source}",
        f"- Title: {item.title or item.id}",
    ]
    summary = _single_line(item.excerpt) or _single_line(item.body)
    if summary:
        lines.append(f"- Summary: {summary}")
    if item.url:
        lines.append(f"- URL: {item.url}")
    return "\n".join(lines).rstrip() + "\n"


def render_location_arrival_mini_digest(items: Iterable[CollectedItem]) -> str | None:
    item = next((value for value in items if value.source == "location_context"), None)
    if item is None:
        return None
    context = item.metadata.get("context") or []
    lines = [
        "# Arrival context",
        "",
        f"- Place: {item.title or item.id}",
    ]
    for value in context:
        lines.append(f"- {value}")
    if item.url:
        lines.append(f"- Map: {item.url}")
    return "\n".join(lines).rstrip() + "\n"


def render_location_dwell_nudge(items: Iterable[CollectedItem]) -> str | None:
    item = next((value for value in items if value.source == "location_context"), None)
    if item is None:
        return None
    context = item.metadata.get("context") or []
    reason = item.metadata.get("detected_reason") or "stopped_moving"
    dwell_minutes = item.metadata.get("dwell_minutes")
    lines = [
        "# Location nudge",
        "",
        f"- Place: {item.title or item.id}",
        f"- Reason: {_render_location_dwell_reason(reason)}",
    ]
    if dwell_minutes is not None:
        lines.append(f"- Dwell: {dwell_minutes} min")
    reason_message = _render_location_dwell_message(reason)
    if reason_message:
        lines.append(f"- {reason_message}")
    for value in context:
        if reason_message and value == reason_message:
            continue
        lines.append(f"- {value}")
    if item.url:
        lines.append(f"- Map: {item.url}")
    return "\n".join(lines).rstrip() + "\n"


def render_trigger_quality_review(items: Iterable[CollectedItem]) -> str | None:
    item = next((value for value in items if value.source == "audit_context"), None)
    if item is None:
        return None
    lines = ["# Trigger quality review", ""]
    for line in (item.body or "").splitlines():
        lines.append(f"- {line}")
    return "\n".join(lines).rstrip() + "\n"


def render_gap_window_mini_digest(items: Iterable[CollectedItem], *, now: datetime) -> str | None:
    calendar_items = [item for item in items if item.source == "google_calendar" and item.timestamps and item.timestamps.start_at]
    if not calendar_items:
        return None
    current_end = None
    next_item = None
    for item in sorted(calendar_items, key=lambda value: value.timestamps.start_at or ""):
        start_at = _parse_timestamp(item.timestamps.start_at)
        end_at = _parse_timestamp(item.timestamps.end_at) if item.timestamps.end_at else start_at
        if end_at <= now:
            current_end = end_at
            continue
        if start_at > now:
            next_item = item
            break
    if current_end is None or next_item is None:
        return None
    gap_minutes = int((_parse_timestamp(next_item.timestamps.start_at) - now).total_seconds() // 60)
    if gap_minutes < 30:
        return None
    lines = [
        "# Gap window",
        "",
        f"- {gap_minutes} min free",
        f"- Next event: {next_item.title or next_item.id}",
        f"- Starts at: {next_item.timestamps.start_at}",
    ]
    return "\n".join(lines).rstrip() + "\n"


def render_feed_update_deep_brief(items: Iterable[CollectedItem]) -> str | None:
    item = _select_primary_feed_item(items)
    if item is None:
        return None
    lines = [
        "# Feed deep brief",
        "",
        f"- Key claim: {item.title or item.id}",
        f"- Why it matters: {_single_line(item.excerpt) or 'Important update from a tracked source.'}",
        "- Source ladder: primary source reviewed first, secondary discovery retained for context.",
    ]
    if item.url:
        lines.append(f"- Primary source URL: {item.url}")
    return "\n".join(lines).rstrip() + "\n"


def render_feed_update_source_audit(items: Iterable[CollectedItem]) -> str | None:
    candidates = [item for item in items if item.source_kind in {"feed_item", "document"}]
    if not candidates:
        return None
    primary = _select_primary_feed_item(candidates)
    secondary = next(
        (
            item
            for item in candidates
            if item is not primary and item.source_kind == "document"
        ),
        None,
    )
    if secondary is None:
        secondary = next(
            (
                item
                for item in candidates
                if item is not primary
                and (item.provenance is None or item.provenance.authority_tier != "primary")
            ),
            None,
        )
    if secondary is None:
        secondary = next((item for item in candidates if item is not primary), None)
    lines = ["# Feed source audit", ""]
    if primary is not None:
        lines.append(f"- Primary source: {primary.title or primary.id}")
    if secondary is not None:
        lines.append(f"- Secondary/discovery source: {secondary.title or secondary.id}")
    return "\n".join(lines).rstrip() + "\n"


def _select_primary_feed_item(items: Iterable[CollectedItem]) -> CollectedItem | None:
    candidates = [item for item in items if item.source_kind in {"feed_item", "document"}]
    if not candidates:
        return None
    candidates.sort(key=lambda item: (0 if item.provenance and item.provenance.authority_tier == "primary" else 1, item.id))
    return candidates[0]


def _render_section(
    section_name: str,
    candidates: list[Candidate],
    items_by_id: dict[str, CollectedItem],
) -> list[str]:
    lines = [f"## {SECTION_TITLES[section_name]}"]
    if not candidates:
        lines.extend(["- None.", ""])
        return lines

    for candidate in candidates[: SECTION_ITEM_LIMITS.get(section_name, 3)]:
        lines.extend(_render_candidate(candidate, items_by_id))

    lines.append("")
    return lines


def _render_candidate(candidate: Candidate, items_by_id: dict[str, CollectedItem]) -> list[str]:
    item = _first_item(candidate, items_by_id)
    if item is None:
        return [f"- {candidate.id}"]

    lines = [f"- {_render_item_title(item)}"]
    summary = _single_line(item.excerpt) or _single_line(item.body)
    if summary:
        lines.append(f"  - {summary}")

    citation_line = _render_citations(item.citation_chain)
    if citation_line:
        lines.append(f"  - {citation_line}")
    elif item.url:
        lines.append(f"  - URL: {item.url}")

    return lines


def _first_item(candidate: Candidate, items_by_id: dict[str, CollectedItem]) -> CollectedItem | None:
    for item_id in candidate.item_ids:
        item = items_by_id.get(item_id)
        if item is not None:
            return item
    return None


def _render_item_title(item: CollectedItem) -> str:
    title = item.title or item.id
    if item.url:
        return f"[{title}]({item.url})"
    return title


def _render_citations(citations: list[CitationLink]) -> str | None:
    if not citations:
        return None

    formatted = ", ".join(
        f"{citation.relation}: [{citation.label}]({citation.url})" for citation in citations
    )
    return f"Citations: {formatted}"


def _single_line(text: str | None) -> str | None:
    if not text:
        return None

    plain_text = _strip_html(text)
    return next((line.strip() for line in plain_text.splitlines() if line.strip()), None)


def _find_leave_now_candidate(items: Iterable[CollectedItem], now: datetime) -> tuple[CollectedItem, datetime, int] | None:
    best: tuple[CollectedItem, datetime, int] | None = None
    for item in items:
        if item.source != "google_calendar" or item.timestamps is None or not item.timestamps.start_at:
            continue
        travel_minutes = item.metadata.get("travel_minutes")
        if not isinstance(travel_minutes, int):
            continue
        start_at = _parse_timestamp(item.timestamps.start_at)
        departure_at = start_at - timedelta(minutes=travel_minutes)
        if now < departure_at:
            continue
        if best is None or departure_at < best[1]:
            best = (item, departure_at, travel_minutes)
    return best


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _parse_key_value_lines(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip().lower()] = value.strip()
    return values


def _render_location_dwell_reason(reason: object) -> str:
    return {
        "meal_window": "meal window",
        "snack_window": "snack window",
        "stopped_moving": "stopped moving",
        "transient_stop": "transient stop",
    }.get(reason, "stopped moving")


def _render_location_dwell_message(reason: object) -> str:
    return {
        "meal_window": "Lunch window is open nearby.",
        "snack_window": "Afternoon snack timing fits this stop.",
        "stopped_moving": "You have paused here long enough to surface local context.",
        "transient_stop": "This stop still looks brief, so keep the context lightweight.",
    }.get(reason, "You have paused here long enough to surface local context.")


def _strip_html(text: str) -> str:
    text_without_tags = HTML_TAG_RE.sub(" ", text)
    plain_text = unescape(text_without_tags)
    return " ".join(plain_text.split())
