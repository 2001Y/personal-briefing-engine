import json
from pathlib import Path

import hermes_pulse.cli
from hermes_pulse.connectors.google_calendar import GoogleCalendarConnector
from hermes_pulse.summarization.base import SummaryArtifact


ROOT = Path(__file__).resolve().parents[1]
CALENDAR_FIXTURE_PATH = ROOT / "fixtures/google_workspace/calendar_events.json"
SOURCE_REGISTRY_PATH = ROOT / "fixtures/source_registry/sample_sources.yaml"


def test_google_calendar_connector_normalizes_events_from_google_workspace_payload() -> None:
    payload = json.loads(CALENDAR_FIXTURE_PATH.read_text())
    connector = GoogleCalendarConnector(runner=lambda: payload)

    items = connector.collect()

    assert [item.id for item in items] == ["google_calendar:event-1", "google_calendar:event-2"]
    assert [item.source_kind for item in items] == ["event", "event"]
    assert items[0].title == "Team Standup"
    assert items[0].people == ["alice@example.com", "bob@example.com"]
    assert items[0].timestamps is not None
    assert items[0].timestamps.start_at == "2026-04-21T09:00:00Z"
    assert items[0].metadata["future_relevance"] is True
    assert items[0].provenance is not None
    assert items[0].provenance.acquisition_mode == "official_api"
    assert items[0].provenance.provider == "google_calendar"


def test_morning_digest_includes_calendar_fixture_items(monkeypatch, tmp_path: Path) -> None:
    calls: list[dict[str, object]] = []

    class StubCodexCliSummarizer:
        def summarize_archive(self, archive_directory: str | Path) -> SummaryArtifact:
            archive_directory = Path(archive_directory)
            raw_items = json.loads((archive_directory / "raw" / "collected-items.json").read_text())
            content = "# Codex Digest\n\n" + "".join(f"- {item['title']}\n" for item in raw_items)
            output_path = archive_directory / "summary" / "codex-digest.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content)
            calls.append({"raw_items": raw_items, "archive_directory": archive_directory})
            return SummaryArtifact(path=output_path, content=content)

    monkeypatch.setattr(hermes_pulse.cli, "CodexCliSummarizer", StubCodexCliSummarizer)
    output_path = tmp_path / "deliveries" / "morning-digest.md"

    assert (
        hermes_pulse.cli.main(
            [
                "morning-digest",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--calendar-fixture",
                str(CALENDAR_FIXTURE_PATH),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    assert any(item["source"] == "google_calendar" for item in calls[0]["raw_items"])
    assert "Team Standup" in output_path.read_text()
