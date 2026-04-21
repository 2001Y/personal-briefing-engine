from pathlib import Path

import pytest

import hermes_pulse.cli
from hermes_pulse.trigger_registry import get_trigger_profile


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REGISTRY_PATH = ROOT / "fixtures/source_registry/sample_sources.yaml"
MEAL_FIXTURE_PATH = ROOT / "fixtures/location/location_walk_meal.json"
SNACK_FIXTURE_PATH = ROOT / "fixtures/location/location_walk_snack.json"
WALK_FIXTURE_PATH = ROOT / "fixtures/location/location_walk_default.json"
STOP_FIXTURE_PATH = ROOT / "fixtures/location/location_walk_stop.json"


def test_trigger_registry_exposes_location_walk_profile() -> None:
    profile = get_trigger_profile("location.walk.default")

    assert profile.family == "event"
    assert profile.event_type == "location.walk"
    assert profile.output_mode == "nudge"
    assert profile.collection_preset == "location_walk"


def test_trigger_registry_rejects_removed_location_dwell_profile_alias() -> None:
    with pytest.raises(KeyError):
        get_trigger_profile("location.dwell.default")


def test_location_walk_writes_meal_window_nudge_while_walking(tmp_path: Path) -> None:
    output_path = tmp_path / "nudges" / "location-walk-meal.md"

    assert (
        hermes_pulse.cli.main(
            [
                "location-walk",
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
    assert "Walking: 9 min" in content
    assert "Lunch window is open along your walk." in content
    assert "https://maps.google.com/?q=Shibuya+Hikarie" in content


def test_location_walk_writes_snack_window_nudge_while_walking(tmp_path: Path) -> None:
    output_path = tmp_path / "nudges" / "location-walk-snack.md"

    assert (
        hermes_pulse.cli.main(
            [
                "location-walk",
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
    assert "Afternoon snack timing fits your walk." in content
    assert "Walking: 7 min" in content
    assert "Ginza Six" in content


def test_location_walk_writes_walking_nudge(tmp_path: Path) -> None:
    output_path = tmp_path / "nudges" / "location-walk.md"

    assert (
        hermes_pulse.cli.main(
            [
                "location-walk",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--location-fixture",
                str(WALK_FIXTURE_PATH),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    content = output_path.read_text()
    assert "You are moving at a walking pace, so nearby options can stay lightweight." in content
    assert "Walking: 11 min" in content
    assert "Tokyo Station" in content


def test_location_walk_still_writes_stationary_nudge_for_stationary_fixture(tmp_path: Path) -> None:
    output_path = tmp_path / "nudges" / "location-walk-stop.md"

    assert (
        hermes_pulse.cli.main(
            [
                "location-walk",
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
    assert "stopped moving" in content
    assert "You have paused here long enough to surface local context." in content
    assert "Walking:" not in content
    assert "Tokyo Station" in content


def test_location_dwell_cli_alias_is_rejected(tmp_path: Path) -> None:
    output_path = tmp_path / "nudges" / "location-dwell-alias.md"

    with pytest.raises(SystemExit):
        hermes_pulse.cli.main(
            [
                "location-dwell",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--location-fixture",
                str(WALK_FIXTURE_PATH),
                "--output",
                str(output_path),
            ]
        )

    assert not output_path.exists()
