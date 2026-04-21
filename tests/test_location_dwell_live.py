from pathlib import Path

import hermes_pulse.connectors.location_context as location_context_module
import hermes_pulse.cli


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REGISTRY_PATH = ROOT / "fixtures/source_registry/sample_sources.yaml"


def test_location_dwell_can_use_live_location_context_runner(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        location_context_module,
        "_run_location_context",
        lambda: {
            "place": "Tokyo Station",
            "maps_url": "https://maps.google.com/?q=Tokyo+Station",
            "context": ["Movement has paused long enough to surface local context."],
            "local_time": "2026-04-20T21:00:00+09:00",
            "dwell_minutes": 18,
            "detected_reason": "stopped_moving",
        },
    )
    output_path = tmp_path / "nudges" / "location-dwell-live.md"

    assert (
        hermes_pulse.cli.main(
            [
                "location-dwell",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    content = output_path.read_text()
    assert "Tokyo Station" in content
    assert "stopped moving" in content


def test_location_dwell_skips_output_when_live_location_context_has_no_data(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(location_context_module, "_run_location_context", lambda: {})
    output_path = tmp_path / "nudges" / "location-dwell-live.md"

    assert (
        hermes_pulse.cli.main(
            [
                "location-dwell",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    assert not output_path.exists()


def test_location_arrival_does_not_use_live_dwell_runner_without_fixture(monkeypatch, tmp_path: Path) -> None:
    def boom() -> dict:
        raise AssertionError("live dwell runner should not be used for arrival without fixture")

    monkeypatch.setattr(location_context_module, "_run_location_context", boom)
    output_path = tmp_path / "nudges" / "location-arrival-live.md"

    assert (
        hermes_pulse.cli.main(
            [
                "location-arrival",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    assert not output_path.exists()
