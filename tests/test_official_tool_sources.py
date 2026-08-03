from pathlib import Path

from hermes_pulse.source_registry import load_source_registry


LAUNCHER_FIXTURE_PATH = Path("fixtures/source_registry/launcher_sources.yaml")

OFFICIAL_TOOL_UPDATE_SOURCES = {
    "openwiki-releases": "https://github.com/langchain-ai/openwiki/releases.atom",
    "deepagentsjs-releases": "https://github.com/langchain-ai/deepagentsjs/releases.atom",
    "hermes-agent-releases": "https://github.com/NousResearch/hermes-agent/releases.atom",
    "codex-cli-releases": "https://github.com/openai/codex/releases.atom",
    "claude-code-releases": "https://github.com/anthropics/claude-code/releases.atom",
    "browser-use-releases": "https://github.com/browser-use/browser-use/releases.atom",
    "context7-releases": "https://github.com/upstash/context7/releases.atom",
    "firecrawl-releases": "https://github.com/firecrawl/firecrawl/releases.atom",
    "xurl-releases": "https://github.com/xdevplatform/xurl/releases.atom",
    "tailscale-blog": "https://tailscale.com/blog/index.xml",
}


def test_launcher_includes_official_tool_update_sources() -> None:
    entries = {entry.id: entry for entry in load_source_registry(LAUNCHER_FIXTURE_PATH)}

    for source_id in OFFICIAL_TOOL_UPDATE_SOURCES:
        assert source_id in entries


def test_official_tool_update_sources_are_primary_bounded_feeds() -> None:
    entries = {entry.id: entry for entry in load_source_registry(LAUNCHER_FIXTURE_PATH)}

    for source_id, rss_url in OFFICIAL_TOOL_UPDATE_SOURCES.items():
        entry = entries[source_id]
        assert entry.source_family == "official_tool_updates", source_id
        assert entry.acquisition_mode in {"rss_poll", "atom_poll"}, source_id
        assert entry.authority_tier == "primary", source_id
        assert entry.rss_url == rss_url, source_id
        assert entry.category_hint == "it", source_id
        assert "developer-tools" in entry.topical_scopes, source_id
        assert entry.item_limit == 10, source_id
        assert entry.requires_primary_confirmation is False, source_id
