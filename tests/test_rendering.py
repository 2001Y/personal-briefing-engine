from hermes_pulse.models import CitationLink, CollectedItem, IntentSignals, Provenance
from hermes_pulse.rendering import render_morning_digest
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
