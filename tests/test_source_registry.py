from pathlib import Path

from hermes_pulse.source_registry import load_source_registry


FIXTURE_PATH = Path("fixtures/source_registry/sample_sources.yaml")


def test_load_source_registry_from_yaml() -> None:
    entries = load_source_registry(FIXTURE_PATH)

    assert len(entries) == 3

    official = entries[0]
    assert official.authority_tier == "primary"
    assert official.rss_url == "https://example.com/feed.xml"
    assert official.search_hints == ["site:example.com official updates"]
    assert official.requires_primary_confirmation is False

    trusted_secondary = entries[1]
    assert trusted_secondary.authority_tier == "trusted_secondary"
    assert trusted_secondary.rss_url == "https://trusted.example.org/atom.xml"
    assert trusted_secondary.requires_primary_confirmation is True

    discovery_only = entries[2]
    assert discovery_only.authority_tier == "discovery_only"
    assert discovery_only.rss_url is None
    assert discovery_only.search_hints == ["site:discover.example.net rumors"]
    assert discovery_only.requires_primary_confirmation is True
