import json
import sqlite3
from pathlib import Path

import pytest

import hermes_pulse.cli
from hermes_pulse.db import initialize_database
from hermes_pulse.db import list_active_suppression_subjects
from hermes_pulse.models import Provenance
from hermes_pulse.summarization.base import SummaryArtifact


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REGISTRY_PATH = ROOT / "fixtures/source_registry/sample_sources.yaml"
HERMES_HISTORY_PATH = ROOT / "fixtures/hermes_history/sample_session.json"
NOTES_PATH = ROOT / "fixtures/notes/sample_notes.md"
CALENDAR_FIXTURE = ROOT / "fixtures/google_workspace/calendar_leave_now_events.json"
AUDIT_FIXTURE = ROOT / "fixtures/audit/trigger_quality.json"
SHOPPING_NOTES_PATH = ROOT / "fixtures/notes/shopping_replenishment.md"


@pytest.fixture(autouse=True)
def _stub_network_connectors(monkeypatch):
    class EmptyFeedRegistryConnector:
        def __init__(self, fetcher=None) -> None:
            self.fetcher = fetcher

        def collect(self, entries):
            return []

    class EmptyKnownSourceSearchConnector:
        def __init__(self, fetcher=None) -> None:
            self.fetcher = fetcher

        def collect(self, entries):
            return []

    monkeypatch.setattr(hermes_pulse.cli, "FeedRegistryConnector", EmptyFeedRegistryConnector)
    monkeypatch.setattr(hermes_pulse.cli, "KnownSourceSearchConnector", EmptyKnownSourceSearchConnector)


def _install_stub_codex_summarizer(monkeypatch, template: str | None = None) -> list[dict[str, object]]:
    calls: list[dict[str, object]] = []

    class StubCodexCliSummarizer:
        def summarize_archive(self, archive_directory: str | Path) -> SummaryArtifact:
            archive_directory = Path(archive_directory)
            raw_items = json.loads((archive_directory / "raw" / "collected-items.json").read_text())
            content = template or "# Codex Digest\n\n" + "".join(
                f"- {item['title']}\n" for item in raw_items
            )
            output_path = archive_directory / "summary" / "codex-digest.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content)
            calls.append(
                {
                    "archive_directory": archive_directory,
                    "raw_items": raw_items,
                    "content": content,
                }
            )
            return SummaryArtifact(path=output_path, content=content)

    monkeypatch.setattr(hermes_pulse.cli, "CodexCliSummarizer", StubCodexCliSummarizer)
    return calls


def test_morning_digest_records_trigger_run_and_delivery_in_state_db(monkeypatch, tmp_path: Path) -> None:
    _install_stub_codex_summarizer(monkeypatch, template="# Codex Digest\n\n- Canonical summary\n")
    database_path = tmp_path / "state" / "hermes-pulse.db"
    output_path = tmp_path / "deliveries" / "morning-digest.md"

    assert (
        hermes_pulse.cli.main(
            [
                "morning-digest",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--hermes-history",
                str(HERMES_HISTORY_PATH),
                "--notes",
                str(NOTES_PATH),
                "--state-db",
                str(database_path),
                "--output",
                str(output_path),
                "--now",
                "2026-04-20T07:30:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        trigger_runs = connection.execute(
            "SELECT event_type, profile_id, output_mode, status FROM trigger_runs"
        ).fetchall()
        deliveries = connection.execute(
            "SELECT destination, status FROM deliveries"
        ).fetchall()
        suppression_history = connection.execute(
            "SELECT trigger_family, reason, cooldown_expires_at, dismissal_status, superseded_by_higher_authority FROM suppression_history ORDER BY subject"
        ).fetchall()

    assert trigger_runs == [("digest.morning", "digest.morning.default", "digest", "completed")]
    assert deliveries == [(str(output_path), "success")]
    assert suppression_history == [
        ("digest.morning", "already_delivered_in_same_trigger_family", "2026-04-21T07:30:00Z", "active", 0),
        ("digest.morning", "already_delivered_in_same_trigger_family", "2026-04-21T07:30:00Z", "active", 0),
    ]


def test_dismiss_suppression_updates_dismissal_status_and_deactivates_subject(monkeypatch, tmp_path: Path) -> None:
    _install_stub_codex_summarizer(monkeypatch, template="# Codex Digest\n\n- Canonical summary\n")
    database_path = tmp_path / "state" / "hermes-pulse.db"
    output_path = tmp_path / "deliveries" / "morning-digest.md"

    assert (
        hermes_pulse.cli.main(
            [
                "morning-digest",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--hermes-history",
                str(HERMES_HISTORY_PATH),
                "--notes",
                str(NOTES_PATH),
                "--state-db",
                str(database_path),
                "--output",
                str(output_path),
                "--now",
                "2026-04-20T07:30:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        suppression_id = connection.execute(
            "SELECT suppression_id FROM suppression_history ORDER BY suppression_id LIMIT 1"
        ).fetchone()[0]

    active_before = list_active_suppression_subjects(
        database_path,
        trigger_family="digest.morning",
        occurred_at="2026-04-20T07:35:00Z",
    )

    assert (
        hermes_pulse.cli.main(
            [
                "dismiss-suppression",
                "--state-db",
                str(database_path),
                "--suppression-id",
                suppression_id,
                "--now",
                "2026-04-20T08:00:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT subject, dismissal_status FROM suppression_history WHERE suppression_id = ?",
            (suppression_id,),
        ).fetchone()

    active_after = list_active_suppression_subjects(
        database_path,
        trigger_family="digest.morning",
        occurred_at="2026-04-20T08:05:00Z",
    )

    assert row[1] == "dismissed"
    assert row[0] in active_before
    assert row[0] not in active_after
    assert len(active_after) == len(active_before) - 1


def test_expire_suppression_updates_dismissal_status_and_deactivates_subject(monkeypatch, tmp_path: Path) -> None:
    _install_stub_codex_summarizer(monkeypatch, template="# Codex Digest\n\n- Canonical summary\n")
    database_path = tmp_path / "state" / "hermes-pulse.db"
    output_path = tmp_path / "deliveries" / "morning-digest.md"

    assert (
        hermes_pulse.cli.main(
            [
                "morning-digest",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--hermes-history",
                str(HERMES_HISTORY_PATH),
                "--notes",
                str(NOTES_PATH),
                "--state-db",
                str(database_path),
                "--output",
                str(output_path),
                "--now",
                "2026-04-20T07:30:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        suppression_id = connection.execute(
            "SELECT suppression_id FROM suppression_history ORDER BY suppression_id LIMIT 1"
        ).fetchone()[0]

    active_before = list_active_suppression_subjects(
        database_path,
        trigger_family="digest.morning",
        occurred_at="2026-04-20T07:35:00Z",
    )

    assert (
        hermes_pulse.cli.main(
            [
                "expire-suppression",
                "--state-db",
                str(database_path),
                "--suppression-id",
                suppression_id,
                "--now",
                "2026-04-20T08:00:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT subject, dismissal_status FROM suppression_history WHERE suppression_id = ?",
            (suppression_id,),
        ).fetchone()

    active_after = list_active_suppression_subjects(
        database_path,
        trigger_family="digest.morning",
        occurred_at="2026-04-20T08:05:00Z",
    )

    assert row[1] == "expired"
    assert row[0] in active_before
    assert row[0] not in active_after
    assert len(active_after) == len(active_before) - 1


def test_dismiss_suppression_rejects_unknown_suppression_id(tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "hermes-pulse.db"

    with pytest.raises(ValueError, match="suppression not found"):
        hermes_pulse.cli.main(
            [
                "dismiss-suppression",
                "--state-db",
                str(database_path),
                "--suppression-id",
                "missing-suppression-id",
                "--now",
                "2026-04-20T08:00:00Z",
            ]
        )


def test_supersede_suppression_marks_higher_authority_and_deactivates_subject(monkeypatch, tmp_path: Path) -> None:
    _install_stub_codex_summarizer(monkeypatch, template="# Codex Digest\n\n- Canonical summary\n")
    database_path = tmp_path / "state" / "hermes-pulse.db"
    output_path = tmp_path / "deliveries" / "morning-digest.md"

    assert (
        hermes_pulse.cli.main(
            [
                "morning-digest",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--hermes-history",
                str(HERMES_HISTORY_PATH),
                "--notes",
                str(NOTES_PATH),
                "--state-db",
                str(database_path),
                "--output",
                str(output_path),
                "--now",
                "2026-04-20T07:30:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        suppression_id = connection.execute(
            "SELECT suppression_id FROM suppression_history ORDER BY suppression_id LIMIT 1"
        ).fetchone()[0]

    active_before = list_active_suppression_subjects(
        database_path,
        trigger_family="digest.morning",
        occurred_at="2026-04-20T07:35:00Z",
    )

    assert (
        hermes_pulse.cli.main(
            [
                "supersede-suppression",
                "--state-db",
                str(database_path),
                "--suppression-id",
                suppression_id,
                "--now",
                "2026-04-20T08:00:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT subject, dismissal_status, superseded_by_higher_authority FROM suppression_history WHERE suppression_id = ?",
            (suppression_id,),
        ).fetchone()

    active_after = list_active_suppression_subjects(
        database_path,
        trigger_family="digest.morning",
        occurred_at="2026-04-20T08:05:00Z",
    )

    assert row[1:] == ("active", 1)
    assert row[0] in active_before
    assert row[0] not in active_after
    assert len(active_after) == len(active_before) - 1


def test_supersede_suppression_rejects_unknown_suppression_id(tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "hermes-pulse.db"

    with pytest.raises(ValueError, match="suppression not found"):
        hermes_pulse.cli.main(
            [
                "supersede-suppression",
                "--state-db",
                str(database_path),
                "--suppression-id",
                "missing-suppression-id",
                "--now",
                "2026-04-20T08:00:00Z",
            ]
        )


def test_supersede_suppression_rejects_already_superseded_row(monkeypatch, tmp_path: Path) -> None:
    _install_stub_codex_summarizer(monkeypatch, template="# Codex Digest\n\n- Canonical summary\n")
    database_path = tmp_path / "state" / "hermes-pulse.db"
    output_path = tmp_path / "deliveries" / "morning-digest.md"

    assert (
        hermes_pulse.cli.main(
            [
                "morning-digest",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--hermes-history",
                str(HERMES_HISTORY_PATH),
                "--notes",
                str(NOTES_PATH),
                "--state-db",
                str(database_path),
                "--output",
                str(output_path),
                "--now",
                "2026-04-20T07:30:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        suppression_id = connection.execute(
            "SELECT suppression_id FROM suppression_history ORDER BY suppression_id LIMIT 1"
        ).fetchone()[0]

    assert (
        hermes_pulse.cli.main(
            [
                "supersede-suppression",
                "--state-db",
                str(database_path),
                "--suppression-id",
                suppression_id,
                "--now",
                "2026-04-20T08:00:00Z",
            ]
        )
        == 0
    )

    with pytest.raises(ValueError, match="already superseded"):
        hermes_pulse.cli.main(
            [
                "supersede-suppression",
                "--state-db",
                str(database_path),
                "--suppression-id",
                suppression_id,
                "--now",
                "2026-04-20T08:05:00Z",
            ]
        )


def test_morning_digest_records_source_registry_state(monkeypatch, tmp_path: Path) -> None:
    _install_stub_codex_summarizer(monkeypatch, template="# Codex Digest\n\n- Canonical summary\n")
    database_path = tmp_path / "state" / "hermes-pulse.db"

    class FakeFeedRegistryConnector:
        def __init__(self, fetcher=None) -> None:
            self.fetcher = fetcher

        def collect(self, entries):
            return [
                hermes_pulse.cli.CollectedItem(
                    id="official-blog:post-2",
                    source="official-blog",
                    source_kind="feed_item",
                    title="Official post",
                    provenance=Provenance(
                        provider="example.com",
                        acquisition_mode="rss_poll",
                        authority_tier="primary",
                        primary_source_url="https://example.com/posts/2",
                        raw_record_id="post-2",
                    ),
                ),
                hermes_pulse.cli.CollectedItem(
                    id="trusted-secondary-blog:entry-9",
                    source="trusted-secondary-blog",
                    source_kind="feed_item",
                    title="Analyst note",
                    provenance=Provenance(
                        provider="trusted.example.org",
                        acquisition_mode="atom_poll",
                        authority_tier="trusted_secondary",
                        primary_source_url="https://trusted.example.org/posts/9",
                        raw_record_id="entry-9",
                    ),
                ),
            ]

    class FakeKnownSourceSearchConnector:
        def __init__(self, fetcher=None) -> None:
            self.fetcher = fetcher

        def collect(self, entries):
            return [
                hermes_pulse.cli.CollectedItem(
                    id="discovery-only-source:https://discover.example.net/story",
                    source="discovery-only-source",
                    source_kind="document",
                    title="Discovery result",
                    provenance=Provenance(
                        provider="discover.example.net",
                        acquisition_mode="known_source_search",
                        authority_tier="discovery_only",
                        primary_source_url="https://discover.example.net/story",
                        raw_record_id="https://discover.example.net/story",
                    ),
                )
            ]

    monkeypatch.setattr(hermes_pulse.cli, "FeedRegistryConnector", FakeFeedRegistryConnector)
    monkeypatch.setattr(hermes_pulse.cli, "KnownSourceSearchConnector", FakeKnownSourceSearchConnector)

    assert (
        hermes_pulse.cli.main(
            [
                "morning-digest",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--state-db",
                str(database_path),
                "--now",
                "2026-04-20T07:30:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        registry_state = connection.execute(
            "SELECT registry_id, last_poll_at, last_seen_item_ids, last_promoted_item_ids, authority_tier FROM source_registry_state ORDER BY registry_id"
        ).fetchall()

    assert registry_state == [
        (
            "discovery-only-source",
            "2026-04-20T07:30:00Z",
            '["discovery-only-source:https://discover.example.net/story"]',
            '["discovery-only-source:https://discover.example.net/story"]',
            "discovery_only",
        ),
        (
            "official-blog",
            "2026-04-20T07:30:00Z",
            '["official-blog:post-2"]',
            '["official-blog:post-2"]',
            "primary",
        ),
        (
            "trusted-secondary-blog",
            "2026-04-20T07:30:00Z",
            '["trusted-secondary-blog:entry-9"]',
            '["trusted-secondary-blog:entry-9"]',
            "trusted_secondary",
        ),
    ]


def test_source_registry_state_updates_promoted_ids_and_preserves_notes(monkeypatch, tmp_path: Path) -> None:
    _install_stub_codex_summarizer(monkeypatch, template="# Codex Digest\n\n- Canonical summary\n")
    database_path = tmp_path / "state" / "hermes-pulse.db"
    initialize_database(database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO source_registry_state (registry_id, last_poll_at, last_seen_item_ids, last_promoted_item_ids, authority_tier, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "official-blog",
                "2026-04-19T07:00:00Z",
                '["official-blog:post-1"]',
                '["official-blog:post-1"]',
                "primary",
                '{"review_note": "keep this note"}',
            ),
        )
        connection.commit()

    class FakeFeedRegistryConnector:
        def __init__(self, fetcher=None) -> None:
            self.fetcher = fetcher

        def collect(self, entries):
            return [
                hermes_pulse.cli.CollectedItem(
                    id="official-blog:post-2",
                    source="official-blog",
                    source_kind="feed_item",
                    title="Official post",
                    provenance=Provenance(
                        provider="example.com",
                        acquisition_mode="rss_poll",
                        authority_tier="primary",
                        primary_source_url="https://example.com/posts/2",
                        raw_record_id="post-2",
                    ),
                )
            ]

    monkeypatch.setattr(hermes_pulse.cli, "FeedRegistryConnector", FakeFeedRegistryConnector)

    assert (
        hermes_pulse.cli.main(
            [
                "morning-digest",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--state-db",
                str(database_path),
                "--now",
                "2026-04-20T07:35:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        registry_state = connection.execute(
            "SELECT registry_id, last_poll_at, last_seen_item_ids, last_promoted_item_ids, notes FROM source_registry_state WHERE registry_id = 'official-blog'"
        ).fetchone()

    assert registry_state == (
        "official-blog",
        "2026-04-20T07:35:00Z",
        '["official-blog:post-2"]',
        '["official-blog:post-2"]',
        '{"review_note": "keep this note", "last_error": null}',
    )


def test_source_registry_state_skips_unobserved_sources(monkeypatch, tmp_path: Path) -> None:
    _install_stub_codex_summarizer(monkeypatch, template="# Codex Digest\n\n- Canonical summary\n")
    database_path = tmp_path / "state" / "hermes-pulse.db"

    class FakeFeedRegistryConnector:
        def __init__(self, fetcher=None) -> None:
            self.fetcher = fetcher

        def collect(self, entries):
            return [
                hermes_pulse.cli.CollectedItem(
                    id="official-blog:post-2",
                    source="official-blog",
                    source_kind="feed_item",
                    title="Official post",
                    provenance=Provenance(
                        provider="example.com",
                        acquisition_mode="rss_poll",
                        authority_tier="primary",
                        primary_source_url="https://example.com/posts/2",
                        raw_record_id="post-2",
                    ),
                )
            ]

    class EmptyKnownSourceSearchConnector:
        def __init__(self, fetcher=None) -> None:
            self.fetcher = fetcher

        def collect(self, entries):
            return []

    monkeypatch.setattr(hermes_pulse.cli, "FeedRegistryConnector", FakeFeedRegistryConnector)
    monkeypatch.setattr(hermes_pulse.cli, "KnownSourceSearchConnector", EmptyKnownSourceSearchConnector)

    assert (
        hermes_pulse.cli.main(
            [
                "morning-digest",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--state-db",
                str(database_path),
                "--now",
                "2026-04-20T07:40:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        registry_state = connection.execute(
            "SELECT registry_id FROM source_registry_state ORDER BY registry_id"
        ).fetchall()

    assert registry_state == [("official-blog",)]


def test_source_registry_state_records_error_metadata_without_overwriting_notes(tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "hermes-pulse.db"
    initialize_database(database_path)

    hermes_pulse.cli._record_source_registry_state(
        database_path,
        source_registry=[
            hermes_pulse.cli.SourceRegistryEntry(
                id="official-blog",
                source_family="blog",
                domain="example.com",
                title="Official blog",
                acquisition_mode="rss_poll",
                authority_tier="primary",
            )
        ],
        items=[
            hermes_pulse.cli.CollectedItem(
                id="official-blog:post-2",
                source="official-blog",
                source_kind="feed_item",
                title="Official post",
                provenance=Provenance(
                    provider="example.com",
                    acquisition_mode="rss_poll",
                    authority_tier="primary",
                    primary_source_url="https://example.com/posts/2",
                    raw_record_id="post-2",
                ),
            )
        ],
        occurred_at="2026-04-20T07:45:00Z",
        source_errors={"official-blog": "feed timeout"},
    )

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT notes FROM source_registry_state WHERE registry_id = 'official-blog'"
        ).fetchone()

    assert row == ('{"last_error": "feed timeout"}',)


def test_source_registry_state_records_error_metadata_for_error_only_source(tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "hermes-pulse.db"
    initialize_database(database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO source_registry_state (registry_id, last_poll_at, last_seen_item_ids, last_promoted_item_ids, authority_tier, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "official-blog",
                "2026-04-19T07:00:00Z",
                '["official-blog:post-1"]',
                '["official-blog:post-1"]',
                "primary",
                '{"review_note": "keep this note"}',
            ),
        )
        connection.commit()

    hermes_pulse.cli._record_source_registry_state(
        database_path,
        source_registry=[
            hermes_pulse.cli.SourceRegistryEntry(
                id="official-blog",
                source_family="blog",
                domain="example.com",
                title="Official blog",
                acquisition_mode="rss_poll",
                authority_tier="primary",
            )
        ],
        items=[],
        occurred_at="2026-04-20T07:50:00Z",
        source_errors={"official-blog": "feed timeout"},
    )

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT last_poll_at, last_seen_item_ids, last_promoted_item_ids, notes FROM source_registry_state WHERE registry_id = 'official-blog'"
        ).fetchone()

    assert row == (
        "2026-04-20T07:50:00Z",
        '["official-blog:post-1"]',
        '["official-blog:post-1"]',
        '{"review_note": "keep this note", "last_error": "feed timeout"}',
    )


def test_event_trigger_records_run_without_delivery_when_no_output(monkeypatch, tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "hermes-pulse.db"

    assert (
        hermes_pulse.cli.main(
            [
                "leave-now-warning",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--calendar-fixture",
                str(CALENDAR_FIXTURE),
                "--now",
                "2026-04-20T08:45:00Z",
                "--state-db",
                str(database_path),
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        trigger_runs = connection.execute(
            "SELECT event_type, profile_id, output_mode, status FROM trigger_runs"
        ).fetchall()
        deliveries = connection.execute("SELECT destination, status FROM deliveries").fetchall()

    assert trigger_runs == [("calendar.leave_now", "calendar.leave_now.default", "warning", "completed")]
    assert deliveries == []


def test_review_trigger_quality_records_feedback_log(tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "hermes-pulse.db"

    assert (
        hermes_pulse.cli.main(
            [
                "review-trigger-quality",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--audit-fixture",
                str(AUDIT_FIXTURE),
                "--state-db",
                str(database_path),
                "--now",
                "2026-04-20T12:00:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        feedback_rows = connection.execute(
            "SELECT category, subject, signal, value, recorded_at FROM feedback_log ORDER BY category, signal, subject"
        ).fetchall()

    assert feedback_rows == [
        ("source_quality", "trusted-secondary-blog", "weak_source", "1", "2026-04-20T12:00:00Z"),
        ("trigger_quality", "review.trigger_quality", "delivery_failures", "1", "2026-04-20T12:00:00Z"),
        ("trigger_quality", "review.trigger_quality", "ignored_rate", "9", "2026-04-20T12:00:00Z"),
        ("trigger_quality", "calendar.leave_now", "late_trigger", "1", "2026-04-20T12:00:00Z"),
        ("trigger_quality", "review.trigger_quality", "notification_rate", "14", "2026-04-20T12:00:00Z"),
    ]


def test_shopping_replenishment_records_approval_action_log(tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "hermes-pulse.db"
    output_path = tmp_path / "action-prep" / "shopping.md"

    assert (
        hermes_pulse.cli.main(
            [
                "shopping-replenishment",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--notes",
                str(SHOPPING_NOTES_PATH),
                "--state-db",
                str(database_path),
                "--output",
                str(output_path),
                "--now",
                "2026-04-20T12:05:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        action_rows = connection.execute(
            "SELECT action_kind, subject, approval_boundary_reached, user_decision, execution_result, execution_details, recorded_at FROM approval_action_log"
        ).fetchall()

    assert action_rows == [
        (
            "shopping.replenishment",
            '{"buy": "Coffee beans", "preferred_store": "Kurasu", "link": "https://example.com/products/coffee-beans"}',
            1,
            "pending",
            "not_executed",
            None,
            "2026-04-20T12:05:00Z",
        )
    ]


def test_morning_digest_skips_items_suppressed_in_same_trigger_family(monkeypatch, tmp_path: Path) -> None:
    summarizer_calls = _install_stub_codex_summarizer(monkeypatch)
    database_path = tmp_path / "state" / "hermes-pulse.db"
    first_output_path = tmp_path / "deliveries" / "first.md"
    second_output_path = tmp_path / "deliveries" / "second.md"

    class FakeFeedRegistryConnector:
        def __init__(self, fetcher=None) -> None:
            self.fetcher = fetcher

        def collect(self, entries):
            return [
                hermes_pulse.cli.CollectedItem(
                    id="official-blog:post-1",
                    source="official-blog",
                    source_kind="feed_item",
                    title="Official post 1",
                    provenance=Provenance(
                        provider="example.com",
                        acquisition_mode="rss_poll",
                        authority_tier="primary",
                        primary_source_url="https://example.com/posts/1",
                        raw_record_id="post-1",
                    ),
                ),
                hermes_pulse.cli.CollectedItem(
                    id="official-blog:post-2",
                    source="official-blog",
                    source_kind="feed_item",
                    title="Official post 2",
                    provenance=Provenance(
                        provider="example.com",
                        acquisition_mode="rss_poll",
                        authority_tier="primary",
                        primary_source_url="https://example.com/posts/2",
                        raw_record_id="post-2",
                    ),
                ),
            ]

    monkeypatch.setattr(hermes_pulse.cli, "FeedRegistryConnector", FakeFeedRegistryConnector)

    assert (
        hermes_pulse.cli.main(
            [
                "morning-digest",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--state-db",
                str(database_path),
                "--output",
                str(first_output_path),
                "--now",
                "2026-04-20T07:30:00Z",
            ]
        )
        == 0
    )

    assert (
        hermes_pulse.cli.main(
            [
                "morning-digest",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--state-db",
                str(database_path),
                "--output",
                str(second_output_path),
                "--now",
                "2026-04-20T12:00:00Z",
            ]
        )
        == 0
    )

    assert [item["title"] for item in summarizer_calls[0]["raw_items"]] == ["Official post 1", "Official post 2"]
    assert summarizer_calls[1]["raw_items"] == []
    assert second_output_path.read_text() == "# Codex Digest\n\n"

    with sqlite3.connect(database_path) as connection:
        suppression_count = connection.execute("SELECT COUNT(*) FROM suppression_history").fetchone()[0]
        cursor_row = connection.execute(
            "SELECT cursor, last_poll_at, last_success_at FROM connector_cursors WHERE connector_id = 'official-blog'"
        ).fetchone()

    assert suppression_count == 2
    assert cursor_row is None


def test_approve_action_updates_pending_approval_action(tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "hermes-pulse.db"
    output_path = tmp_path / "action-prep" / "shopping.md"

    assert (
        hermes_pulse.cli.main(
            [
                "shopping-replenishment",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--notes",
                str(SHOPPING_NOTES_PATH),
                "--state-db",
                str(database_path),
                "--output",
                str(output_path),
                "--now",
                "2026-04-20T12:05:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        action_id = connection.execute("SELECT action_id FROM approval_action_log").fetchone()[0]

    assert (
        hermes_pulse.cli.main(
            [
                "approve-action",
                "--state-db",
                str(database_path),
                "--action-id",
                action_id,
                "--now",
                "2026-04-20T12:10:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT user_decision, execution_result, recorded_at FROM approval_action_log WHERE action_id = ?",
            (action_id,),
        ).fetchone()

    assert row == ("approved", "approved_pending_execution", "2026-04-20T12:10:00Z")


def test_reject_action_updates_pending_approval_action(tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "hermes-pulse.db"
    output_path = tmp_path / "action-prep" / "shopping.md"

    assert (
        hermes_pulse.cli.main(
            [
                "shopping-replenishment",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--notes",
                str(SHOPPING_NOTES_PATH),
                "--state-db",
                str(database_path),
                "--output",
                str(output_path),
                "--now",
                "2026-04-20T12:05:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        action_id = connection.execute("SELECT action_id FROM approval_action_log").fetchone()[0]

    assert (
        hermes_pulse.cli.main(
            [
                "reject-action",
                "--state-db",
                str(database_path),
                "--action-id",
                action_id,
                "--now",
                "2026-04-20T12:11:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT user_decision, execution_result, recorded_at FROM approval_action_log WHERE action_id = ?",
            (action_id,),
        ).fetchone()

    assert row == ("rejected", "cancelled", "2026-04-20T12:11:00Z")


def test_approve_action_rejects_unknown_action_id(tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "hermes-pulse.db"

    with pytest.raises(ValueError, match="approval action not found"):
        hermes_pulse.cli.main(
            [
                "approve-action",
                "--state-db",
                str(database_path),
                "--action-id",
                "missing-action-id",
                "--now",
                "2026-04-20T12:12:00Z",
            ]
        )


def test_reject_action_rejects_non_pending_action(tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "hermes-pulse.db"
    output_path = tmp_path / "action-prep" / "shopping.md"

    assert (
        hermes_pulse.cli.main(
            [
                "shopping-replenishment",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--notes",
                str(SHOPPING_NOTES_PATH),
                "--state-db",
                str(database_path),
                "--output",
                str(output_path),
                "--now",
                "2026-04-20T12:05:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        action_id = connection.execute("SELECT action_id FROM approval_action_log").fetchone()[0]

    assert (
        hermes_pulse.cli.main(
            [
                "approve-action",
                "--state-db",
                str(database_path),
                "--action-id",
                action_id,
                "--now",
                "2026-04-20T12:10:00Z",
            ]
        )
        == 0
    )

    with pytest.raises(ValueError, match="approval action is not pending"):
        hermes_pulse.cli.main(
            [
                "reject-action",
                "--state-db",
                str(database_path),
                "--action-id",
                action_id,
                "--now",
                "2026-04-20T12:11:00Z",
            ]
        )


def test_complete_action_updates_approved_action_execution_result(tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "hermes-pulse.db"
    output_path = tmp_path / "action-prep" / "shopping.md"

    assert (
        hermes_pulse.cli.main(
            [
                "shopping-replenishment",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--notes",
                str(SHOPPING_NOTES_PATH),
                "--state-db",
                str(database_path),
                "--output",
                str(output_path),
                "--now",
                "2026-04-20T12:05:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        action_id = connection.execute("SELECT action_id FROM approval_action_log").fetchone()[0]

    assert (
        hermes_pulse.cli.main(
            [
                "approve-action",
                "--state-db",
                str(database_path),
                "--action-id",
                action_id,
                "--now",
                "2026-04-20T12:10:00Z",
            ]
        )
        == 0
    )

    assert (
        hermes_pulse.cli.main(
            [
                "complete-action",
                "--state-db",
                str(database_path),
                "--action-id",
                action_id,
                "--execution-receipt",
                "ordered via amazon",
                "--execution-provider",
                "amazon",
                "--execution-store",
                "Kurasu",
                "--execution-order-id",
                "ORDER-123",
                "--now",
                "2026-04-20T12:15:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT user_decision, execution_result, execution_details, recorded_at FROM approval_action_log WHERE action_id = ?",
            (action_id,),
        ).fetchone()

    assert row == (
        "approved",
        "executed",
        '{"receipt": "ordered via amazon", "provider": "amazon", "store": "Kurasu", "order_id": "ORDER-123"}',
        "2026-04-20T12:15:00Z",
    )

    with sqlite3.connect(database_path) as connection:
        feedback_rows = connection.execute(
            "SELECT category, subject, signal, value, recorded_at FROM feedback_log ORDER BY category, signal, subject"
        ).fetchall()

    assert feedback_rows == [
        ("action_execution", "shopping.replenishment", "executed", "1", "2026-04-20T12:15:00Z")
    ]


def test_complete_action_rejects_unknown_action_id(tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "hermes-pulse.db"

    with pytest.raises(ValueError, match="approval action not found"):
        hermes_pulse.cli.main(
            [
                "complete-action",
                "--state-db",
                str(database_path),
                "--action-id",
                "missing-action-id",
                "--now",
                "2026-04-20T12:15:00Z",
            ]
        )


def test_complete_action_rejects_non_executable_action(tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "hermes-pulse.db"
    output_path = tmp_path / "action-prep" / "shopping.md"

    assert (
        hermes_pulse.cli.main(
            [
                "shopping-replenishment",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--notes",
                str(SHOPPING_NOTES_PATH),
                "--state-db",
                str(database_path),
                "--output",
                str(output_path),
                "--now",
                "2026-04-20T12:05:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        action_id = connection.execute("SELECT action_id FROM approval_action_log").fetchone()[0]

    with pytest.raises(ValueError, match="approval action is not awaiting execution completion"):
        hermes_pulse.cli.main(
            [
                "complete-action",
                "--state-db",
                str(database_path),
                "--action-id",
                action_id,
                "--now",
                "2026-04-20T12:15:00Z",
            ]
        )


def test_complete_action_rejects_execution_error_flag(tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "hermes-pulse.db"

    with pytest.raises(ValueError, match="complete-action does not accept --execution-error or --retryable"):
        hermes_pulse.cli.main(
            [
                "complete-action",
                "--state-db",
                str(database_path),
                "--action-id",
                "missing-action-id",
                "--execution-error",
                "api timeout",
                "--retryable",
                "--now",
                "2026-04-20T12:15:00Z",
            ]
        )


def test_approve_action_rejects_execution_detail_flags(tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "hermes-pulse.db"

    with pytest.raises(ValueError, match="approve-action does not accept execution detail flags"):
        hermes_pulse.cli.main(
            [
                "approve-action",
                "--state-db",
                str(database_path),
                "--action-id",
                "missing-action-id",
                "--execution-receipt",
                "ordered via amazon",
                "--execution-provider",
                "amazon",
                "--execution-order-id",
                "ORDER-123",
                "--retryable",
                "--now",
                "2026-04-20T12:10:00Z",
            ]
        )


def test_failed_action_updates_approved_action_execution_result(tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "hermes-pulse.db"
    output_path = tmp_path / "action-prep" / "shopping.md"

    assert (
        hermes_pulse.cli.main(
            [
                "shopping-replenishment",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--notes",
                str(SHOPPING_NOTES_PATH),
                "--state-db",
                str(database_path),
                "--output",
                str(output_path),
                "--now",
                "2026-04-20T12:05:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        action_id = connection.execute("SELECT action_id FROM approval_action_log").fetchone()[0]

    assert (
        hermes_pulse.cli.main(
            [
                "approve-action",
                "--state-db",
                str(database_path),
                "--action-id",
                action_id,
                "--now",
                "2026-04-20T12:10:00Z",
            ]
        )
        == 0
    )

    assert (
        hermes_pulse.cli.main(
            [
                "failed-action",
                "--state-db",
                str(database_path),
                "--action-id",
                action_id,
                "--execution-error",
                "api timeout",
                "--execution-provider",
                "amazon",
                "--retryable",
                "--now",
                "2026-04-20T12:20:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT user_decision, execution_result, execution_details, recorded_at FROM approval_action_log WHERE action_id = ?",
            (action_id,),
        ).fetchone()

    assert row == (
        "approved",
        "failed",
        '{"error": "api timeout", "provider": "amazon", "retryable": true}',
        "2026-04-20T12:20:00Z",
    )

    with sqlite3.connect(database_path) as connection:
        feedback_rows = connection.execute(
            "SELECT category, subject, signal, value, recorded_at FROM feedback_log ORDER BY category, signal, subject"
        ).fetchall()

    assert feedback_rows == [
        ("action_execution", "shopping.replenishment", "failed", "1", "2026-04-20T12:20:00Z"),
        ("action_execution", "shopping.replenishment", "retryable_failure", "1", "2026-04-20T12:20:00Z"),
    ]


def test_failed_action_rejects_unknown_action_id(tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "hermes-pulse.db"

    with pytest.raises(ValueError, match="approval action not found"):
        hermes_pulse.cli.main(
            [
                "failed-action",
                "--state-db",
                str(database_path),
                "--action-id",
                "missing-action-id",
                "--now",
                "2026-04-20T12:20:00Z",
            ]
        )


def test_failed_action_rejects_execution_receipt_flag(tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "hermes-pulse.db"

    with pytest.raises(ValueError, match="failed-action does not accept --execution-receipt or --execution-order-id"):
        hermes_pulse.cli.main(
            [
                "failed-action",
                "--state-db",
                str(database_path),
                "--action-id",
                "missing-action-id",
                "--execution-receipt",
                "ordered via amazon",
                "--execution-order-id",
                "ORDER-123",
                "--now",
                "2026-04-20T12:20:00Z",
            ]
        )


def test_reject_action_rejects_execution_detail_flags(tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "hermes-pulse.db"

    with pytest.raises(ValueError, match="reject-action does not accept execution detail flags"):
        hermes_pulse.cli.main(
            [
                "reject-action",
                "--state-db",
                str(database_path),
                "--action-id",
                "missing-action-id",
                "--execution-error",
                "api timeout",
                "--execution-provider",
                "amazon",
                "--retryable",
                "--now",
                "2026-04-20T12:11:00Z",
            ]
        )


def test_failed_action_rejects_non_executable_action(tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "hermes-pulse.db"
    output_path = tmp_path / "action-prep" / "shopping.md"

    assert (
        hermes_pulse.cli.main(
            [
                "shopping-replenishment",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--notes",
                str(SHOPPING_NOTES_PATH),
                "--state-db",
                str(database_path),
                "--output",
                str(output_path),
                "--now",
                "2026-04-20T12:05:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        action_id = connection.execute("SELECT action_id FROM approval_action_log").fetchone()[0]

    with pytest.raises(ValueError, match="approval action is not awaiting execution completion"):
        hermes_pulse.cli.main(
            [
                "failed-action",
                "--state-db",
                str(database_path),
                "--action-id",
                action_id,
                "--now",
                "2026-04-20T12:20:00Z",
            ]
        )


def test_delivery_failure_marks_trigger_run_failed(monkeypatch, tmp_path: Path) -> None:
    _install_stub_codex_summarizer(monkeypatch, template="# Codex Digest\n\n- Canonical summary\n")
    database_path = tmp_path / "state" / "hermes-pulse.db"
    output_path = tmp_path / "deliveries" / "morning-digest.md"

    class ExplodingDelivery:
        def deliver(self, content: str, destination: str | Path) -> Path:
            raise OSError("disk full")

    monkeypatch.setattr(hermes_pulse.cli, "LocalMarkdownDelivery", lambda: ExplodingDelivery())

    try:
        hermes_pulse.cli.main(
            [
                "morning-digest",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--hermes-history",
                str(HERMES_HISTORY_PATH),
                "--notes",
                str(NOTES_PATH),
                "--state-db",
                str(database_path),
                "--output",
                str(output_path),
            ]
        )
    except OSError as exc:
        assert str(exc) == "disk full"
    else:
        raise AssertionError("delivery failure should propagate")

    with sqlite3.connect(database_path) as connection:
        trigger_runs = connection.execute(
            "SELECT event_type, profile_id, output_mode, status FROM trigger_runs"
        ).fetchall()
        deliveries = connection.execute("SELECT destination, status FROM deliveries").fetchall()

    assert trigger_runs == [("digest.morning", "digest.morning.default", "digest", "failed")]
    assert deliveries == []


def test_summarization_failure_still_records_failed_trigger_run(monkeypatch, tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "hermes-pulse.db"

    class ExplodingSummarizer:
        def summarize_archive(self, archive_directory: str | Path):
            raise RuntimeError("codex unavailable")

    monkeypatch.setattr(hermes_pulse.cli, "CodexCliSummarizer", lambda: ExplodingSummarizer())

    try:
        hermes_pulse.cli.main(
            [
                "morning-digest",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--hermes-history",
                str(HERMES_HISTORY_PATH),
                "--notes",
                str(NOTES_PATH),
                "--state-db",
                str(database_path),
            ]
        )
    except RuntimeError as exc:
        assert str(exc) == "codex unavailable"
    else:
        raise AssertionError("summarization failure should propagate")

    with sqlite3.connect(database_path) as connection:
        trigger_runs = connection.execute(
            "SELECT event_type, profile_id, output_mode, status FROM trigger_runs"
        ).fetchall()

    assert trigger_runs == [("digest.morning", "digest.morning.default", "digest", "failed")]


def test_delivery_state_logging_failure_uses_delivery_state_error_status(monkeypatch, tmp_path: Path) -> None:
    _install_stub_codex_summarizer(monkeypatch, template="# Codex Digest\n\n- Canonical summary\n")
    database_path = tmp_path / "state" / "hermes-pulse.db"
    output_path = tmp_path / "deliveries" / "morning-digest.md"

    def exploding_record_delivery(*args, **kwargs):
        raise RuntimeError("db write failed")

    monkeypatch.setattr(hermes_pulse.cli, "record_delivery", exploding_record_delivery)

    try:
        hermes_pulse.cli.main(
            [
                "morning-digest",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--hermes-history",
                str(HERMES_HISTORY_PATH),
                "--notes",
                str(NOTES_PATH),
                "--state-db",
                str(database_path),
                "--output",
                str(output_path),
            ]
        )
    except RuntimeError as exc:
        assert str(exc) == "db write failed"
    else:
        raise AssertionError("delivery state logging failure should propagate")

    assert output_path.exists()
    with sqlite3.connect(database_path) as connection:
        trigger_runs = connection.execute(
            "SELECT event_type, profile_id, output_mode, status FROM trigger_runs"
        ).fetchall()
        deliveries = connection.execute("SELECT destination, status FROM deliveries").fetchall()

    assert trigger_runs == [("digest.morning", "digest.morning.default", "digest", "delivery_state_error")]
    assert deliveries == []


def test_morning_digest_state_db_uses_explicit_now_timestamp(monkeypatch, tmp_path: Path) -> None:
    _install_stub_codex_summarizer(monkeypatch, template="# Codex Digest\n\n- Canonical summary\n")
    database_path = tmp_path / "state" / "hermes-pulse.db"
    occurred_at = "2020-01-01T00:00:00Z"
    collected_trigger_times: list[str] = []
    original_collect_for_trigger = hermes_pulse.cli.collect_for_trigger

    def capture_collect_for_trigger(trigger, profile, connectors):
        collected_trigger_times.append(trigger.occurred_at)
        return original_collect_for_trigger(trigger, profile, connectors)

    monkeypatch.setattr(hermes_pulse.cli, "collect_for_trigger", capture_collect_for_trigger)

    assert (
        hermes_pulse.cli.main(
            [
                "morning-digest",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--hermes-history",
                str(HERMES_HISTORY_PATH),
                "--notes",
                str(NOTES_PATH),
                "--state-db",
                str(database_path),
                "--now",
                occurred_at,
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        stored_occurred_at = connection.execute(
            "SELECT occurred_at FROM trigger_runs"
        ).fetchone()

    assert stored_occurred_at == (occurred_at,)
    assert collected_trigger_times == [occurred_at]


def test_completed_status_write_failure_downgrades_to_delivery_state_error(monkeypatch, tmp_path: Path) -> None:
    _install_stub_codex_summarizer(monkeypatch, template="# Codex Digest\n\n- Canonical summary\n")
    database_path = tmp_path / "state" / "hermes-pulse.db"
    output_path = tmp_path / "deliveries" / "morning-digest.md"
    original_update = hermes_pulse.cli.update_trigger_run_status

    def flaky_update(path, *, run_id: str, status: str) -> None:
        if status == "completed":
            raise RuntimeError("final status write failed")
        original_update(path, run_id=run_id, status=status)

    monkeypatch.setattr(hermes_pulse.cli, "update_trigger_run_status", flaky_update)

    try:
        hermes_pulse.cli.main(
            [
                "morning-digest",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--hermes-history",
                str(HERMES_HISTORY_PATH),
                "--notes",
                str(NOTES_PATH),
                "--state-db",
                str(database_path),
                "--output",
                str(output_path),
            ]
        )
    except RuntimeError as exc:
        assert str(exc) == "final status write failed"
    else:
        raise AssertionError("completed status write failure should propagate")

    assert output_path.exists()
    with sqlite3.connect(database_path) as connection:
        trigger_runs = connection.execute(
            "SELECT status FROM trigger_runs"
        ).fetchall()

    assert trigger_runs == [("delivery_state_error",)]


def test_morning_digest_records_x_signal_connector_cursors(monkeypatch, tmp_path: Path) -> None:
    _install_stub_codex_summarizer(monkeypatch, template="# Codex Digest\n\n- Canonical summary\n")
    database_path = tmp_path / "state" / "hermes-pulse.db"

    class FakeXConnector:
        def collect(self, signal_types: list[str]):
            assert signal_types == ["bookmarks", "likes"]
            return [
                hermes_pulse.cli.CollectedItem(
                    id="x-bookmarks:tweet-150",
                    source="x_bookmarks",
                    source_kind="post",
                    title="Older saved thread",
                    provenance=Provenance(
                        provider="x.com",
                        acquisition_mode="official_api",
                        authority_tier="primary",
                        primary_source_url="https://x.com/example/status/150",
                        raw_record_id="150",
                    ),
                ),
                hermes_pulse.cli.CollectedItem(
                    id="x-bookmarks:tweet-200",
                    source="x_bookmarks",
                    source_kind="post",
                    title="Saved launch thread",
                    provenance=Provenance(
                        provider="x.com",
                        acquisition_mode="official_api",
                        authority_tier="primary",
                        primary_source_url="https://x.com/example/status/200",
                        raw_record_id="200",
                    ),
                ),
                hermes_pulse.cli.CollectedItem(
                    id="x-likes:tweet-90",
                    source="x_likes",
                    source_kind="post",
                    title="Liked post",
                    provenance=Provenance(
                        provider="x.com",
                        acquisition_mode="official_api",
                        authority_tier="primary",
                        primary_source_url="https://x.com/example/status/90",
                        raw_record_id="90",
                    ),
                ),
            ]

    monkeypatch.setattr(hermes_pulse.cli, "XUrlConnector", FakeXConnector)

    assert (
        hermes_pulse.cli.main(
            [
                "morning-digest",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--x-signals",
                "bookmarks,likes",
                "--state-db",
                str(database_path),
                "--now",
                "2026-04-20T08:00:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        cursors = connection.execute(
            "SELECT connector_id, cursor, last_poll_at, last_success_at FROM connector_cursors ORDER BY connector_id"
        ).fetchall()

    assert cursors == [
        ("x_bookmarks", "200", "2026-04-20T08:00:00Z", "2026-04-20T08:00:00Z"),
        ("x_likes", "90", "2026-04-20T08:00:00Z", "2026-04-20T08:00:00Z"),
    ]


def test_morning_digest_records_empty_x_signal_poll_as_successful_cursor_refresh(monkeypatch, tmp_path: Path) -> None:
    _install_stub_codex_summarizer(monkeypatch, template="# Codex Digest\n\n- Canonical summary\n")
    database_path = tmp_path / "state" / "hermes-pulse.db"

    class EmptyXConnector:
        def collect(self, signal_types: list[str]):
            assert signal_types == ["bookmarks", "likes"]
            return []

    monkeypatch.setattr(hermes_pulse.cli, "XUrlConnector", EmptyXConnector)

    assert (
        hermes_pulse.cli.main(
            [
                "morning-digest",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--x-signals",
                "bookmarks,likes",
                "--state-db",
                str(database_path),
                "--now",
                "2026-04-20T09:00:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        cursors = connection.execute(
            "SELECT connector_id, cursor, last_poll_at, last_success_at FROM connector_cursors ORDER BY connector_id"
        ).fetchall()

    assert cursors == [
        ("x_bookmarks", None, "2026-04-20T09:00:00Z", "2026-04-20T09:00:00Z"),
        ("x_likes", None, "2026-04-20T09:00:00Z", "2026-04-20T09:00:00Z"),
    ]


def test_empty_x_signal_poll_preserves_existing_cursor(monkeypatch, tmp_path: Path) -> None:
    _install_stub_codex_summarizer(monkeypatch, template="# Codex Digest\n\n- Canonical summary\n")
    database_path = tmp_path / "state" / "hermes-pulse.db"

    class BookmarkXConnector:
        def collect(self, signal_types: list[str]):
            return [
                hermes_pulse.cli.CollectedItem(
                    id="x-bookmarks:tweet-200",
                    source="x_bookmarks",
                    source_kind="post",
                    title="Saved launch thread",
                    provenance=Provenance(
                        provider="x.com",
                        acquisition_mode="official_api",
                        authority_tier="primary",
                        primary_source_url="https://x.com/example/status/200",
                        raw_record_id="200",
                    ),
                )
            ]

    monkeypatch.setattr(hermes_pulse.cli, "XUrlConnector", BookmarkXConnector)
    assert (
        hermes_pulse.cli.main(
            [
                "morning-digest",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--x-signals",
                "bookmarks",
                "--state-db",
                str(database_path),
                "--now",
                "2026-04-20T09:05:00Z",
            ]
        )
        == 0
    )

    class EmptyBookmarkXConnector:
        def collect(self, signal_types: list[str]):
            return []

    monkeypatch.setattr(hermes_pulse.cli, "XUrlConnector", EmptyBookmarkXConnector)
    assert (
        hermes_pulse.cli.main(
            [
                "morning-digest",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--x-signals",
                "bookmarks",
                "--state-db",
                str(database_path),
                "--now",
                "2026-04-20T09:10:00Z",
            ]
        )
        == 0
    )

    with sqlite3.connect(database_path) as connection:
        cursor = connection.execute(
            "SELECT connector_id, cursor, last_poll_at, last_success_at FROM connector_cursors WHERE connector_id = 'x_bookmarks'"
        ).fetchone()

    assert cursor == ("x_bookmarks", "200", "2026-04-20T09:10:00Z", "2026-04-20T09:10:00Z")


def test_failed_digest_does_not_advance_x_signal_cursor(monkeypatch, tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "hermes-pulse.db"

    class FakeXConnector:
        def collect(self, signal_types: list[str]):
            return [
                hermes_pulse.cli.CollectedItem(
                    id="x-bookmarks:tweet-200",
                    source="x_bookmarks",
                    source_kind="post",
                    title="Saved launch thread",
                    provenance=Provenance(
                        provider="x.com",
                        acquisition_mode="official_api",
                        authority_tier="primary",
                        primary_source_url="https://x.com/example/status/200",
                        raw_record_id="200",
                    ),
                )
            ]

    class ExplodingSummarizer:
        def summarize_archive(self, archive_directory: str | Path):
            raise RuntimeError("codex unavailable")

    monkeypatch.setattr(hermes_pulse.cli, "XUrlConnector", FakeXConnector)
    monkeypatch.setattr(hermes_pulse.cli, "CodexCliSummarizer", lambda: ExplodingSummarizer())

    try:
        hermes_pulse.cli.main(
            [
                "morning-digest",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--x-signals",
                "bookmarks",
                "--state-db",
                str(database_path),
                "--now",
                "2026-04-20T09:15:00Z",
            ]
        )
    except RuntimeError as exc:
        assert str(exc) == "codex unavailable"
    else:
        raise AssertionError("summarization failure should propagate")

    with sqlite3.connect(database_path) as connection:
        cursors = connection.execute(
            "SELECT connector_id, cursor, last_poll_at, last_success_at FROM connector_cursors"
        ).fetchall()

    assert cursors == []


def test_failed_digest_does_not_persist_source_registry_state(monkeypatch, tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "hermes-pulse.db"

    class FakeFeedRegistryConnector:
        def __init__(self, fetcher=None) -> None:
            self.fetcher = fetcher

        def collect(self, entries):
            return [
                hermes_pulse.cli.CollectedItem(
                    id="official-blog:post-2",
                    source="official-blog",
                    source_kind="feed_item",
                    title="Official post",
                    provenance=Provenance(
                        provider="example.com",
                        acquisition_mode="rss_poll",
                        authority_tier="primary",
                        primary_source_url="https://example.com/posts/2",
                        raw_record_id="post-2",
                    ),
                )
            ]

    class ExplodingSummarizer:
        def summarize_archive(self, archive_directory: str | Path):
            raise RuntimeError("codex unavailable")

    monkeypatch.setattr(hermes_pulse.cli, "FeedRegistryConnector", FakeFeedRegistryConnector)
    monkeypatch.setattr(hermes_pulse.cli, "CodexCliSummarizer", lambda: ExplodingSummarizer())

    try:
        hermes_pulse.cli.main(
            [
                "morning-digest",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--state-db",
                str(database_path),
                "--now",
                "2026-04-20T09:20:00Z",
            ]
        )
    except RuntimeError as exc:
        assert str(exc) == "codex unavailable"
    else:
        raise AssertionError("summarization failure should propagate")

    with sqlite3.connect(database_path) as connection:
        registry_state = connection.execute(
            "SELECT registry_id FROM source_registry_state"
        ).fetchall()

    assert registry_state == []
