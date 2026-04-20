from hermes_pulse.collection import collect_for_trigger
from hermes_pulse.models import TriggerEvent, TriggerScope
from hermes_pulse.trigger_registry import get_trigger_profile


class StubConnector:
    def __init__(self, connector_id: str) -> None:
        self.id = connector_id
        self.calls = 0

    def collect(self) -> list[str]:
        self.calls += 1
        return [self.id]


def test_broad_day_start_invokes_expected_connectors_only() -> None:
    profile = get_trigger_profile("digest.morning.default")
    trigger = TriggerEvent(
        id="trigger-1",
        type=profile.event_type,
        profile_id=profile.id,
        occurred_at="2026-04-20T08:00:00Z",
        scope=TriggerScope(),
    )
    feed = StubConnector("feed_registry")
    known_source_search = StubConnector("known_source_search")
    x_signals = StubConnector("x_signals")
    google_calendar = StubConnector("google_calendar")
    gmail = StubConnector("gmail")
    hermes_history = StubConnector("hermes_history")
    notes = StubConnector("notes")
    unrelated = StubConnector("unrelated")

    collected = collect_for_trigger(
        trigger,
        profile,
        {
            feed.id: feed,
            known_source_search.id: known_source_search,
            x_signals.id: x_signals,
            google_calendar.id: google_calendar,
            gmail.id: gmail,
            hermes_history.id: hermes_history,
            notes.id: notes,
            unrelated.id: unrelated,
        },
    )

    assert collected == ["feed_registry", "known_source_search", "x_signals", "google_calendar", "gmail", "hermes_history", "notes"]
    assert feed.calls == 1
    assert known_source_search.calls == 1
    assert x_signals.calls == 1
    assert google_calendar.calls == 1
    assert gmail.calls == 1
    assert hermes_history.calls == 1
    assert notes.calls == 1
    assert unrelated.calls == 0


def test_broad_day_start_skips_missing_optional_connectors() -> None:
    profile = get_trigger_profile("digest.morning.default")
    trigger = TriggerEvent(
        id="trigger-1",
        type=profile.event_type,
        profile_id=profile.id,
        occurred_at="2026-04-20T08:00:00Z",
        scope=TriggerScope(),
    )
    feed = StubConnector("feed_registry")

    collected = collect_for_trigger(
        trigger,
        profile,
        {
            feed.id: feed,
        },
    )

    assert collected == ["feed_registry"]
    assert feed.calls == 1


def test_broad_day_end_invokes_expected_connectors_only() -> None:
    profile = get_trigger_profile("digest.evening.default")
    trigger = TriggerEvent(
        id="trigger-2",
        type=profile.event_type,
        profile_id=profile.id,
        occurred_at="2026-04-20T20:00:00Z",
        scope=TriggerScope(),
    )
    feed = StubConnector("feed_registry")
    known_source_search = StubConnector("known_source_search")
    x_signals = StubConnector("x_signals")
    google_calendar = StubConnector("google_calendar")
    gmail = StubConnector("gmail")
    hermes_history = StubConnector("hermes_history")
    notes = StubConnector("notes")

    collected = collect_for_trigger(
        trigger,
        profile,
        {
            feed.id: feed,
            known_source_search.id: known_source_search,
            x_signals.id: x_signals,
            google_calendar.id: google_calendar,
            gmail.id: gmail,
            hermes_history.id: hermes_history,
            notes.id: notes,
        },
    )

    assert collected == ["feed_registry", "known_source_search", "x_signals", "google_calendar", "gmail", "hermes_history", "notes"]
    assert feed.calls == 1
    assert known_source_search.calls == 1
    assert x_signals.calls == 1
    assert google_calendar.calls == 1
    assert gmail.calls == 1
    assert hermes_history.calls == 1
    assert notes.calls == 1


def test_calendar_leave_now_invokes_calendar_connector_only() -> None:
    profile = get_trigger_profile("calendar.leave_now.default")
    trigger = TriggerEvent(
        id="trigger-3",
        type=profile.event_type,
        profile_id=profile.id,
        occurred_at="2026-04-21T08:30:00Z",
        scope=TriggerScope(),
    )
    google_calendar = StubConnector("google_calendar")
    gmail = StubConnector("gmail")
    notes = StubConnector("notes")

    collected = collect_for_trigger(
        trigger,
        profile,
        {
            google_calendar.id: google_calendar,
            gmail.id: gmail,
            notes.id: notes,
        },
    )

    assert collected == ["google_calendar"]
    assert google_calendar.calls == 1
    assert gmail.calls == 0
    assert notes.calls == 0
