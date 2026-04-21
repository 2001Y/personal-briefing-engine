from pathlib import Path

import hermes_pulse.connectors.location_context as location_context_module
import hermes_pulse.cli


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REGISTRY_PATH = ROOT / "fixtures/source_registry/sample_sources.yaml"


def test_location_walk_can_use_live_location_context_runner(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        location_context_module,
        "_run_location_context",
        lambda: {
            "place": "Tokyo Station",
            "maps_url": "https://maps.google.com/?q=Tokyo+Station",
            "context": ["You are moving at a walking pace, so nearby options can stay lightweight."],
            "local_time": "2026-04-20T21:00:00+09:00",
            "walking_minutes": 8,
            "average_speed_m_s": 1.3,
            "detected_reason": "walking_nearby",
        },
    )
    output_path = tmp_path / "nudges" / "location-walk-live.md"

    assert (
        hermes_pulse.cli.main(
            [
                "location-walk",
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
    assert "walking nearby" in content


def test_location_walk_skips_output_when_live_location_context_has_no_data(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(location_context_module, "_run_location_context", lambda: {})
    output_path = tmp_path / "nudges" / "location-walk-live.md"

    assert (
        hermes_pulse.cli.main(
            [
                "location-walk",
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    assert not output_path.exists()


def test_location_arrival_does_not_use_live_walk_runner_without_fixture(monkeypatch, tmp_path: Path) -> None:
    def boom() -> dict:
        raise AssertionError("live walk runner should not be used for arrival without fixture")

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
