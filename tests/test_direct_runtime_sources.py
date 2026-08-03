from pathlib import Path

from hermes_pulse.source_registry import load_source_registry


LAUNCHER_PATH = Path("fixtures/source_registry/launcher_sources.yaml")

RUNTIME_TOOL_SOURCE_IDS = {
    "bun-releases",
    "uv-releases",
    "nodejs-releases",
    "python-releases",
    "github-cli-releases",
    "chezmoi-releases",
    "playwright-releases",
    "quartz-releases",
    "remotion-releases",
    "gsap-releases",
    "cloudflare-workers-sdk-releases",
    "bitwarden-clients-releases",
    "supabase-releases",
    "langchainjs-releases",
    "langgraphjs-releases",
    "langsmith-sdk-releases",
    "mcp-typescript-sdk-releases",
    "openai-python-releases",
    "openai-node-releases",
    "anthropic-typescript-releases",
}

PYPI_DIRECT_DEPENDENCY_NAMES = {
    "openai",
    "certifi",
    "python-dotenv",
    "fire",
    "httpx",
    "rich",
    "tenacity",
    "pyyaml",
    "ruamel-yaml",
    "requests",
    "jinja2",
    "pydantic",
    "prompt-toolkit",
    "croniter",
    "packaging",
    "markdown",
    "pyjwt",
    "urllib3",
    "cryptography",
    "psutil",
    "websockets",
    "pathspec",
    "fastapi",
    "uvicorn",
    "python-multipart",
    "ptyprocess",
    "tzdata",
    "pywinpty",
    "pywin32",
    "pillow",
    "concurrent-log-handler",
}



def test_launcher_includes_all_direct_runtime_and_toolchain_sources() -> None:
    entries = {entry.id: entry for entry in load_source_registry(LAUNCHER_PATH)}
    expected_pypi_ids = {f"pypi-{name}-releases" for name in PYPI_DIRECT_DEPENDENCY_NAMES}
    expected_ids = RUNTIME_TOOL_SOURCE_IDS | expected_pypi_ids

    assert expected_ids <= entries.keys()

    for source_id in expected_ids:
        entry = entries[source_id]
        assert entry.authority_tier == "primary"
        assert entry.category_hint == "it"
        assert entry.item_limit == 5
        assert entry.requires_primary_confirmation is False
        assert entry.rss_url


def test_direct_python_dependencies_use_pypi_release_rss() -> None:
    entries = {entry.id: entry for entry in load_source_registry(LAUNCHER_PATH)}

    for name in PYPI_DIRECT_DEPENDENCY_NAMES:
        entry = entries[f"pypi-{name}-releases"]
        pypi_project = "ruamel.yaml" if name == "ruamel-yaml" else name
        assert entry.domain == "pypi.org"
        assert entry.acquisition_mode == "rss_poll"
        assert entry.rss_url == f"https://pypi.org/rss/project/{pypi_project}/releases.xml"
        assert entry.source_family == "official_library_updates"
