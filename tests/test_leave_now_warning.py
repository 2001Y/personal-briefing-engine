from pathlib import Path

import hermes_pulse.cli


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REGISTRY_PATH = ROOT / "fixtures/source_registry/sample_sources.yaml"
CALENDAR_FIXTURE_PATH = ROOT / "fixtures/google_workspace/calendar_leave_now_events.json"


def test_trigger_registry_exposes_calendar_leave_now_warning_profile() -> None:
    profile = hermes_pulse.cli.get_trigger_profile("calendar.leave_now.default")

    assert profile.family == "event"
    assert profile.event_type == "calendar.leave_now"
    assert profile.output_mode == "warning"
    assert profile.collection_preset == "calendar_leave_now"


def test_leave_now_warning_writes_high_urgency_message_when_departure_time_has_arrived(tmp_path: Path) -> None:
    output_path = tmp_path / "warnings" / "leave-now.md"

    assert (
        hermes_pulse.cli.main(
            [
                "leave-now-warning",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--calendar-fixture",
                str(CALENDAR_FIXTURE_PATH),
                "--now",
                "2026-04-21T08:30:00Z",
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    warning = output_path.read_text()
    assert warning.startswith("# Leave now")
    assert "Airport drop-off" in warning
    assert "Haneda Airport" in warning
    assert "Travel estimate: 35 min" in warning
    assert "Recommended departure: 2026-04-21T08:25:00Z" in warning


def test_leave_now_warning_skips_output_when_no_event_is_past_departure_threshold(tmp_path: Path) -> None:
    output_path = tmp_path / "warnings" / "leave-now.md"

    assert (
        hermes_pulse.cli.main(
            [
                "leave-now-warning",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--calendar-fixture",
                str(CALENDAR_FIXTURE_PATH),
                "--now",
                "2026-04-21T07:30:00Z",
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    assert not output_path.exists()
