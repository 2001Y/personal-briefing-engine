from hermes_pulse.models import CitationLink, CollectedItem, IntentSignals, Provenance
from hermes_pulse.rendering import (
    render_location_dwell_nudge,
    render_location_walk_nudge,
    render_morning_digest,
)
from hermes_pulse.synthesis import synthesize_candidates


def make_item(
    item_id: str,
    *,
    title: str,
    source: str = "notes",
    source_kind: str = "note",
    authority_tier: str | None = None,
    future_relevance: bool = False,
    open_loop: bool = False,
    saved: bool = False,
    excerpt: str | None = None,
    body: str | None = None,
    url: str | None = None,
) -> CollectedItem:
    acquisition_mode = "rss_poll" if source_kind == "feed_item" else "local_store"
    citation_chain = []
    if url:
        relation = "primary" if authority_tier == "primary" else "secondary"
        citation_chain = [CitationLink(label=title, url=url, relation=relation)]

    return CollectedItem(
        id=item_id,
        source=source,
        source_kind=source_kind,
        title=title,
        excerpt=excerpt,
        body=body,
        url=url,
        intent_signals=IntentSignals(saved=saved, unresolved=open_loop),
        provenance=Provenance(
            provider=source,
            acquisition_mode=acquisition_mode,
            authority_tier=authority_tier,
            primary_source_url=url,
        ),
        citation_chain=citation_chain,
        metadata={"future_relevance": future_relevance},
    )


def test_render_morning_digest_includes_ranked_sections_and_source_links() -> None:
    items = [
        make_item("today-note", title="Prep agenda", future_relevance=True),
        make_item("incoming-note", title="Inbox triage"),
        make_item("followup-note", title="Reply to Dana", open_loop=True),
        make_item("resurface-note", title="Revisit hiring rubric", saved=True),
        make_item(
            "feed-update",
            title="Launch update",
            source="official-blog",
            source_kind="feed_item",
            authority_tier="primary",
            excerpt="Version 1.0 ships today.",
            url="https://example.com/posts/launch-update",
        ),
    ]

    digest = render_morning_digest(synthesize_candidates(items), items)

    assert digest.startswith("# Morning Digest")
    assert digest.index("## Today") < digest.index("## Incoming")
    assert digest.index("## Incoming") < digest.index("## Followup")
    assert digest.index("## Followup") < digest.index("## Resurface")
    assert digest.index("## Resurface") < digest.index("## Feed updates")

    assert "Prep agenda" in digest
    assert "Inbox triage" in digest
    assert "Reply to Dana" in digest
    assert "Revisit hiring rubric" in digest
    assert "Launch update" in digest
    assert "https://example.com/posts/launch-update" in digest
    assert "Citations:" in digest


def test_render_morning_digest_omits_feed_updates_when_no_authoritative_feed_items() -> None:
    items = [
        make_item("incoming-note", title="Inbox triage"),
    ]

    digest = render_morning_digest(synthesize_candidates(items), items)

    assert "## Today" in digest
    assert "## Incoming" in digest
    assert "## Followup" in digest
    assert "## Resurface" in digest
    assert "## Feed updates" not in digest


def test_render_morning_digest_caps_each_section_to_three_items() -> None:
    items = [
        *(make_item(f"today-{index:02d}", title=f"Today {index:02d}", future_relevance=True) for index in range(1, 5)),
        *(make_item(f"incoming-{index:02d}", title=f"Incoming {index:02d}") for index in range(1, 5)),
        *(make_item(f"followup-{index:02d}", title=f"Followup {index:02d}", open_loop=True) for index in range(1, 5)),
        *(make_item(f"resurface-{index:02d}", title=f"Resurface {index:02d}", saved=True) for index in range(1, 5)),
        *(
            make_item(
                f"feed-{index:02d}",
                title=f"Feed {index:02d}",
                source=f"feed-{index:02d}",
                source_kind="feed_item",
                authority_tier="primary",
                excerpt=f"Feed summary {index:02d}",
                url=f"https://example.com/feed-{index:02d}",
            )
            for index in range(1, 5)
        ),
    ]

    digest = render_morning_digest(synthesize_candidates(items), items)

    for prefix in ("Today", "Incoming", "Followup", "Resurface", "Feed"):
        assert f"{prefix} 01" in digest
        assert f"{prefix} 02" in digest
        assert f"{prefix} 03" in digest
        assert f"{prefix} 04" not in digest


def test_render_morning_digest_strips_html_from_summaries() -> None:
    items = [
        make_item(
            "today-html",
            title="Today HTML",
            future_relevance=True,
            excerpt="<p>Hello <strong>world</strong> &amp; team</p>",
        ),
        make_item(
            "incoming-html",
            title="Incoming HTML",
            body="<div>Body <em>summary</em> line</div>",
        ),
    ]

    digest = render_morning_digest(synthesize_candidates(items), items)

    assert "Hello world & team" in digest
    assert "Body summary line" in digest
    assert "<p>" not in digest
    assert "<strong>" not in digest
    assert "<div>" not in digest
    assert "<em>" not in digest


def test_render_location_walk_nudge_defaults_stationary_items_without_detected_reason() -> None:
    item = CollectedItem(
        id="location_context:tokyo-station",
        source="location_context",
        source_kind="place",
        title="Tokyo Station",
        url="https://maps.google.com/?q=Tokyo+Station",
        metadata={
            "context": ["Check whether there is enough buffer for the next train."],
            "dwell_minutes": 21,
        },
    )

    markdown = render_location_walk_nudge([item])

    assert markdown is not None
    assert "Reason: stopped moving" in markdown
    assert "Dwell: 21 min" in markdown
    assert "Walking:" not in markdown
    assert "You have paused here long enough to surface local context." in markdown


def test_render_location_dwell_nudge_alias_matches_location_walk_nudge() -> None:
    item = CollectedItem(
        id="location_context:walking",
        source="location_context",
        source_kind="place",
        title="Walking",
        metadata={"walking_minutes": 6, "detected_reason": "future_reason"},
    )

    assert render_location_dwell_nudge([item]) == render_location_walk_nudge([item])


def test_render_location_walk_nudge_normalizes_unknown_reason_by_motion_mode() -> None:
    stationary_item = CollectedItem(
        id="location_context:stationary",
        source="location_context",
        source_kind="place",
        title="Stationary",
        metadata={"dwell_minutes": 18, "detected_reason": "future_reason"},
    )
    walking_item = CollectedItem(
        id="location_context:walking",
        source="location_context",
        source_kind="place",
        title="Walking",
        metadata={"walking_minutes": 6, "detected_reason": "future_reason"},
    )

    stationary_markdown = render_location_walk_nudge([stationary_item])
    walking_markdown = render_location_walk_nudge([walking_item])

    assert stationary_markdown is not None and "Reason: stopped moving" in stationary_markdown
    assert walking_markdown is not None and "Reason: walking nearby" in walking_markdown
