from collections.abc import Iterable

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


def _render_section(
    section_name: str,
    candidates: list[Candidate],
    items_by_id: dict[str, CollectedItem],
) -> list[str]:
    lines = [f"## {SECTION_TITLES[section_name]}"]
    if not candidates:
        lines.extend(["- None.", ""])
        return lines

    for candidate in candidates:
        lines.extend(_render_candidate(candidate, items_by_id))

    lines.append("")
    return lines


def _render_candidate(candidate: Candidate, items_by_id: dict[str, CollectedItem]) -> list[str]:
    item = _first_item(candidate, items_by_id)
    if item is None:
        return [f"- {candidate.id}"]

    lines = [f"- {_render_item_title(item)}"]
    summary = item.excerpt or _single_line(item.body)
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
    return next((line.strip() for line in text.splitlines() if line.strip()), None)
