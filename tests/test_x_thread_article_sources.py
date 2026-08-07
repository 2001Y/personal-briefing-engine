from pathlib import Path

from hermes_pulse.source_registry import load_source_registry


LAUNCHER_FIXTURE_PATH = Path("fixtures/source_registry/launcher_sources.yaml")


EXPECTED_SOURCES = {
    "huggingface-blog": "https://huggingface.co/blog/feed.xml",
    "aisi-blog": "https://www.aisi.gov.uk/sitemap.xml",
    "groundlevel-ai": "https://www.groundlevel-ai.com/feed",
    "cybersecurity-dive": "https://www.cybersecuritydive.com/feeds/news/",
    "wired-security": "https://www.wired.com/feed/category/security/latest/rss",
}


def test_x_thread_article_sites_are_in_launcher_registry_with_bounded_sources() -> None:
    entries = {entry.id: entry for entry in load_source_registry(LAUNCHER_FIXTURE_PATH)}

    assert set(EXPECTED_SOURCES) <= entries.keys()
    for source_id, feed_url in EXPECTED_SOURCES.items():
        entry = entries[source_id]
        assert entry.rss_url == feed_url
        assert entry.item_limit == 10
        assert entry.acquisition_mode == "rss_poll"
        assert entry.topical_scopes

    assert entries["huggingface-blog"].authority_tier == "primary"
    assert entries["aisi-blog"].authority_tier == "primary"
    for source_id in ("groundlevel-ai", "cybersecurity-dive", "wired-security"):
        assert entries[source_id].authority_tier == "trusted_secondary"
        assert entries[source_id].requires_primary_confirmation is True
