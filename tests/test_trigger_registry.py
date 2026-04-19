from hermes_pulse.trigger_registry import get_trigger_profile


def test_digest_morning_default_profile_matches_plan() -> None:
    profile = get_trigger_profile("digest.morning.default")

    assert profile.family == "scheduled"
    assert profile.event_type == "digest.morning"
    assert profile.output_mode == "digest"
    assert profile.collection_preset == "broad_day_start"
