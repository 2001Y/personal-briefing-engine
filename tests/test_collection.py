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
    hermes_history = StubConnector("hermes_history")
    notes = StubConnector("notes")
    unrelated = StubConnector("unrelated")

    collected = collect_for_trigger(
        trigger,
        profile,
        {
            feed.id: feed,
            hermes_history.id: hermes_history,
            notes.id: notes,
            unrelated.id: unrelated,
        },
    )

    assert collected == ["feed_registry", "hermes_history", "notes"]
    assert feed.calls == 1
    assert hermes_history.calls == 1
    assert notes.calls == 1
    assert unrelated.calls == 0
