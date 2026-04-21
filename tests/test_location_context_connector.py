import hermes_pulse.connectors.location_context as location_context_module
from hermes_pulse.connectors.location_context import LocationContextConnector
from datetime import datetime, timezone


def test_location_context_connector_uses_live_runner_when_no_runner_is_provided(monkeypatch) -> None:
    monkeypatch.setattr(
        location_context_module,
        "_run_location_context",
        lambda: {
            "place": "Shibuya Hikarie",
            "maps_url": "https://maps.google.com/?q=Shibuya+Hikarie",
            "context": ["Lunch window is open along your walk."],
            "local_time": "2026-04-20T12:00:00+09:00",
            "walking_minutes": 9,
            "average_speed_m_s": 1.4,
            "detected_reason": "meal_window",
        },
    )

    items = LocationContextConnector().collect()

    assert [item.title for item in items] == ["Shibuya Hikarie"]
    assert items[0].metadata["detected_reason"] == "meal_window"
    assert items[0].metadata["walking_minutes"] == 9
    assert items[0].url == "https://maps.google.com/?q=Shibuya+Hikarie"


def test_location_context_connector_returns_no_items_when_live_runner_has_no_data(monkeypatch) -> None:
    monkeypatch.setattr(location_context_module, "_run_location_context", lambda: {})

    assert LocationContextConnector().collect() == []


def test_location_context_connector_returns_no_items_when_live_runner_errors(monkeypatch) -> None:
    def boom() -> dict:
        raise FileNotFoundError("missing dawarich env")

    monkeypatch.setattr(location_context_module, "_run_location_context", boom)

    assert LocationContextConnector().collect() == []


def test_location_context_connector_propagates_explicit_runner_errors() -> None:
    def boom() -> dict:
        raise ValueError("bad fixture")

    connector = LocationContextConnector(runner=boom)

    try:
        connector.collect()
    except ValueError as exc:
        assert str(exc) == "bad fixture"
    else:
        raise AssertionError("explicit runner errors should propagate")


def test_detect_dwell_payload_returns_walking_candidate_for_walking_speed_points() -> None:
    payload = location_context_module._detect_dwell_payload(
        [
            {"timestamp": 1_713_650_400, "lat": 35.6804, "lon": 139.7690, "accuracy": 10.0, "velocity": 1.5},
            {"timestamp": 1_713_650_220, "lat": 35.6796, "lon": 139.7684, "accuracy": 10.0, "velocity": 1.4},
            {"timestamp": 1_713_650_040, "lat": 35.6788, "lon": 139.7678, "accuracy": 10.0, "velocity": 1.3},
        ],
        now=datetime.fromtimestamp(1_713_650_400, tz=timezone.utc),
        dwell_radius_m=80.0,
        min_dwell_minutes=15,
        max_staleness_minutes=90,
    )

    assert payload is not None
    assert payload["detected_reason"] == "walking_nearby"
    assert payload["walking_minutes"] == 6
    assert payload["average_speed_m_s"] > 1.0


def test_detect_dwell_payload_returns_no_candidate_for_fast_points() -> None:
    payload = location_context_module._detect_dwell_payload(
        [
            {"timestamp": 1_713_675_000, "lat": 35.6804, "lon": 139.7690, "accuracy": 10.0, "velocity": 4.5},
            {"timestamp": 1_713_674_820, "lat": 35.6770, "lon": 139.7660, "accuracy": 10.0, "velocity": 4.2},
            {"timestamp": 1_713_674_640, "lat": 35.6736, "lon": 139.7630, "accuracy": 10.0, "velocity": 4.0},
        ],
        now=datetime.fromtimestamp(1_713_675_000, tz=timezone.utc),
        dwell_radius_m=80.0,
        min_dwell_minutes=15,
        max_staleness_minutes=90,
    )

    assert payload is None
