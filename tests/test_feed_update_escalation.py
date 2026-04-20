from pathlib import Path

import hermes_pulse.cli
from hermes_pulse.trigger_registry import get_trigger_profile


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REGISTRY_PATH = ROOT / "fixtures/source_registry/sample_sources.yaml"
FEED_FIXTURE_PATH = ROOT / "fixtures/feed_samples/official_feed.xml"
SEARCH_FIXTURE_PATH = ROOT / "fixtures/search_samples/known_source_results.html"


def test_trigger_registry_exposes_feed_update_expert_depth_profile() -> None:
    profile = get_trigger_profile("feed.update.expert_depth")

    assert profile.family == "event"
    assert profile.event_type == "feed.update"
    assert profile.output_mode == "deep_brief"
    assert profile.collection_preset == "known_source_deep_dive"


def test_trigger_registry_exposes_feed_update_source_audit_profile() -> None:
    profile = get_trigger_profile("feed.update.source_audit")

    assert profile.family == "event"
    assert profile.event_type == "feed.update"
    assert profile.output_mode == "source_audit"
    assert profile.collection_preset == "known_source_delta"


def test_feed_update_deep_brief_writes_expanded_summary(tmp_path: Path) -> None:
    output_path = tmp_path / "deep-brief" / "feed-update.md"

    assert (
        hermes_pulse.cli.main(
            [
                "feed-update-deep-brief",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--feed-fixture",
                str(FEED_FIXTURE_PATH),
                "--search-fixture",
                str(SEARCH_FIXTURE_PATH),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    content = output_path.read_text()
    assert content.startswith("# Feed deep brief")
    assert "Launch update" in content
    assert "Why it matters" in content
    assert "Source ladder" in content


def test_feed_update_source_audit_writes_primary_vs_secondary_summary(tmp_path: Path) -> None:
    output_path = tmp_path / "source-audit" / "feed-update.md"

    assert (
        hermes_pulse.cli.main(
            [
                "feed-update-source-audit",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--feed-fixture",
                str(FEED_FIXTURE_PATH),
                "--search-fixture",
                str(SEARCH_FIXTURE_PATH),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    content = output_path.read_text()
    assert content.startswith("# Feed source audit")
    assert "Primary source" in content
    assert "Launch update" in content
    assert "Discovery scoop" in content
