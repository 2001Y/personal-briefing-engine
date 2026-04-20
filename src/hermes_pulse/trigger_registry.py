from hermes_pulse.models import TriggerProfile


TRIGGER_REGISTRY = {
    "digest.morning.default": TriggerProfile(
        id="digest.morning.default",
        family="scheduled",
        event_type="digest.morning",
        collection_preset="broad_day_start",
        output_mode="digest",
        action_ceiling=1,
        cooldown_minutes=360,
        quotas={"feed_items": 3, "resurface_items": 3, "people_bundles": 2},
    ),
    "digest.evening.default": TriggerProfile(
        id="digest.evening.default",
        family="scheduled",
        event_type="digest.evening",
        collection_preset="broad_day_end",
        output_mode="digest",
        action_ceiling=1,
        cooldown_minutes=360,
        quotas={"feed_items": 3, "resurface_items": 3, "people_bundles": 2},
    ),
    "calendar.leave_now.default": TriggerProfile(
        id="calendar.leave_now.default",
        family="event",
        event_type="calendar.leave_now",
        collection_preset="calendar_leave_now",
        output_mode="warning",
        action_ceiling=1,
        cooldown_minutes=15,
    ),
}


def get_trigger_profile(profile_id: str) -> TriggerProfile:
    return TRIGGER_REGISTRY[profile_id]
