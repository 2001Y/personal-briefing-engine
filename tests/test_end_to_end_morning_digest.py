from pathlib import Path

import hermes_pulse.cli
from hermes_pulse.collection import collect_for_trigger
from hermes_pulse.connectors.feed_registry import FeedRegistryConnector
from hermes_pulse.connectors.hermes_history import HermesHistoryConnector
from hermes_pulse.connectors.notes import NotesConnector
from hermes_pulse.models import TriggerEvent, TriggerScope
from hermes_pulse.source_registry import load_source_registry
from hermes_pulse.synthesis import synthesize_candidates
from hermes_pulse.trigger_registry import get_trigger_profile


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REGISTRY_PATH = ROOT / "fixtures/source_registry/sample_sources.yaml"
FEED_FIXTURE_PATH = ROOT / "fixtures/feed_samples/official_feed.xml"
HERMES_HISTORY_PATH = ROOT / "fixtures/hermes_history/sample_session.json"
NOTES_PATH = ROOT / "fixtures/notes/sample_notes.md"


class BoundConnector:
    def __init__(self, collector):
        self._collector = collector

    def collect(self):
        return self._collector()


def test_end_to_end_scheduled_morning_digest_runs_against_fixtures(tmp_path: Path) -> None:
    profile = get_trigger_profile("digest.morning.default")
    assert profile.event_type == "digest.morning"
    assert profile.collection_preset == "broad_day_start"

    source_registry = load_source_registry(SOURCE_REGISTRY_PATH)
    assert [entry.id for entry in source_registry] == [
        "official-blog",
        "trusted-secondary-blog",
        "discovery-only-source",
    ]

    trigger = TriggerEvent(
        id="trigger-1",
        type=profile.event_type,
        profile_id=profile.id,
        occurred_at="2026-04-20T08:00:00Z",
        scope=TriggerScope(),
    )
    feed_fixture = FEED_FIXTURE_PATH.read_text()
    collected = collect_for_trigger(
        trigger,
        profile,
        {
            "feed_registry": BoundConnector(
                lambda: FeedRegistryConnector(fetcher=lambda url: feed_fixture).collect(source_registry)
            ),
            "hermes_history": BoundConnector(lambda: HermesHistoryConnector().collect(HERMES_HISTORY_PATH)),
            "notes": BoundConnector(lambda: NotesConnector().collect(NOTES_PATH)),
        },
    )

    assert {item.source for item in collected} == {
        "official-blog",
        "trusted-secondary-blog",
        "hermes_history",
        "notes",
    }

    candidates = synthesize_candidates(collected)

    assert candidates
    assert candidates[0].score >= candidates[-1].score
    assert any(candidate.item_ids[0].startswith("official-blog:") for candidate in candidates)
    assert any(candidate.item_ids == ["session-123"] for candidate in candidates)
    assert any(candidate.item_ids == ["sample_notes"] for candidate in candidates)

    output_path = tmp_path / "deliveries" / "morning-digest.md"

    assert (
        hermes_pulse.cli.main(
            [
                "morning-digest",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--feed-fixture",
                str(FEED_FIXTURE_PATH),
                "--hermes-history",
                str(HERMES_HISTORY_PATH),
                "--notes",
                str(NOTES_PATH),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    markdown = output_path.read_text()
    assert output_path.exists()
    assert markdown.startswith("# Morning Digest\n")
    assert "Launch update" in markdown
    assert "Morning planning" in markdown
    assert "Notes" in markdown
    assert "https://example.com/posts/launch-update" in markdown
    assert "Citations: primary: [Launch update](https://example.com/posts/launch-update)" in markdown
