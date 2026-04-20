from pathlib import Path

import hermes_pulse.cli
from hermes_pulse.trigger_registry import get_trigger_profile


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REGISTRY_PATH = ROOT / "fixtures/source_registry/sample_sources.yaml"
MEAL_FIXTURE_PATH = ROOT / "fixtures/location/location_dwell_meal.json"
SNACK_FIXTURE_PATH = ROOT / "fixtures/location/location_dwell_snack.json"
STOP_FIXTURE_PATH = ROOT / "fixtures/location/location_dwell_stop.json"


def test_trigger_registry_exposes_location_dwell_profile() -> None:
    profile = get_trigger_profile("location.dwell.default")

    assert profile.family == "event"
    assert profile.event_type == "location.dwell"
    assert profile.output_mode == "nudge"
    assert profile.collection_preset == "location_dwell"


def test_location_dwell_writes_meal_window_nudge(tmp_path: Path) -> None:
    output_path = tmp_path / "nudges" / "location-dwell-meal.md"

    assert (
        hermes_pulse.cli.main(
            [
                "location-dwell",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--location-fixture",
                str(MEAL_FIXTURE_PATH),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    content = output_path.read_text()
    assert content.startswith("# Location nudge")
    assert "Shibuya Hikarie" in content
    assert "meal window" in content
    assert "Lunch window is open nearby." in content
    assert "https://maps.google.com/?q=Shibuya+Hikarie" in content


def test_location_dwell_writes_snack_window_nudge(tmp_path: Path) -> None:
    output_path = tmp_path / "nudges" / "location-dwell-snack.md"

    assert (
        hermes_pulse.cli.main(
            [
                "location-dwell",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--location-fixture",
                str(SNACK_FIXTURE_PATH),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    content = output_path.read_text()
    assert "Afternoon snack timing fits this stop." in content
    assert "Ginza Six" in content


def test_location_dwell_writes_stopped_moving_nudge(tmp_path: Path) -> None:
    output_path = tmp_path / "nudges" / "location-dwell-stop.md"

    assert (
        hermes_pulse.cli.main(
            [
                "location-dwell",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--location-fixture",
                str(STOP_FIXTURE_PATH),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    content = output_path.read_text()
    assert "You have paused here long enough to surface local context." in content
    assert "Tokyo Station" in content
