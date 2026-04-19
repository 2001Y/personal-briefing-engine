from dataclasses import fields

from hermes_pulse import models


def field_names(model: type[object]) -> set[str]:
    return {field.name for field in fields(model)}


def test_trigger_event_exposes_documented_fields() -> None:
    assert field_names(models.TriggerEvent) >= {
        "id",
        "type",
        "profile_id",
        "occurred_at",
        "scope",
        "evidence_refs",
        "metadata",
    }


def test_trigger_profile_exposes_documented_fields() -> None:
    assert field_names(models.TriggerProfile) >= {
        "id",
        "family",
        "event_type",
        "collection_preset",
        "output_mode",
        "action_ceiling",
        "cooldown_minutes",
        "ranking_weights",
        "quotas",
    }


def test_source_registry_entry_exposes_documented_fields() -> None:
    assert field_names(models.SourceRegistryEntry) >= {
        "id",
        "source_family",
        "domain",
        "title",
        "acquisition_mode",
        "authority_tier",
        "rss_url",
        "search_hints",
        "topical_scopes",
        "language",
        "requires_primary_confirmation",
    }


def test_collected_item_exposes_documented_fields() -> None:
    assert field_names(models.CollectedItem) >= {
        "id",
        "source",
        "source_kind",
        "title",
        "excerpt",
        "body",
        "url",
        "people",
        "topics",
        "place_refs",
        "timestamps",
        "intent_signals",
        "provenance",
        "citation_chain",
        "metadata",
    }


def test_candidate_exposes_documented_fields() -> None:
    assert field_names(models.Candidate) >= {
        "id",
        "kind",
        "item_ids",
        "trigger_relevance",
        "actionability",
        "score",
        "reasons",
        "suppression_scope",
    }
