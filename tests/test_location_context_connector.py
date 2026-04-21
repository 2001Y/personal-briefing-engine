import hermes_pulse.connectors.location_context as location_context_module
from hermes_pulse.connectors.location_context import LocationContextConnector


def test_location_context_connector_uses_live_runner_when_no_runner_is_provided(monkeypatch) -> None:
    monkeypatch.setattr(
        location_context_module,
        "_run_location_context",
        lambda: {
            "place": "Shibuya Hikarie",
            "maps_url": "https://maps.google.com/?q=Shibuya+Hikarie",
            "context": ["Meal timing is open for this stop."],
            "local_time": "2026-04-20T12:00:00+09:00",
            "dwell_minutes": 42,
            "detected_reason": "meal_window",
        },
    )

    items = LocationContextConnector().collect()

    assert [item.title for item in items] == ["Shibuya Hikarie"]
    assert items[0].metadata["detected_reason"] == "meal_window"
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
