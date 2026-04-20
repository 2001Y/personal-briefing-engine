import json
from pathlib import Path

import pytest

from hermes_pulse.summarization.base import SummaryArtifact
from hermes_pulse.summarization.codex_cli import CodexCliSummarizer


class StubCodexInvocation:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def run(self, prompt: str, *, cwd: Path) -> str:
        self.calls.append({"prompt": prompt, "cwd": cwd})
        return self.response


def test_codex_cli_summarizer_builds_grounded_prompt_and_writes_canonical_digest(tmp_path: Path) -> None:
    archive_directory = tmp_path / "2026-04-20"
    raw_directory = archive_directory / "raw"
    summary_directory = archive_directory / "summary"
    raw_directory.mkdir(parents=True)
    summary_directory.mkdir(parents=True)

    raw_items = [
        {
            "id": "official-blog:launch",
            "source": "official-blog",
            "title": "Launch update",
            "excerpt": "Version 1.0 ships today.",
            "url": "https://example.com/posts/launch-update",
        }
    ]
    (raw_directory / "collected-items.json").write_text(json.dumps(raw_items, indent=2) + "\n")
    (summary_directory / "morning-digest.md").write_text(
        "# Morning Digest\n\n- [Launch update](https://example.com/posts/launch-update)\n"
    )

    invocation = StubCodexInvocation("# Codex Digest\n\n- 日本語の要約\n")
    summarizer = CodexCliSummarizer(invocation=invocation)

    artifact = summarizer.summarize_archive(archive_directory)

    assert artifact == SummaryArtifact(
        path=archive_directory / "summary" / "codex-digest.md",
        content="# Codex Digest\n\n- 日本語の要約\n",
    )
    assert artifact.path.exists()
    assert artifact.path.read_text() == artifact.content
    assert len(invocation.calls) == 1
    assert invocation.calls[0]["cwd"] == archive_directory

    prompt = invocation.calls[0]["prompt"]
    assert isinstance(prompt, str)
    assert "日本語" in prompt
    assert "一次情報" in prompt
    assert "リンク" in prompt
    assert "https://example.com/posts/launch-update" in prompt
    assert '"official-blog:launch"' in prompt
    assert "# Morning Digest" in prompt


def test_codex_cli_summarizer_compacts_large_raw_items_before_prompting(tmp_path: Path) -> None:
    archive_directory = tmp_path / "2026-04-20"
    raw_directory = archive_directory / "raw"
    raw_directory.mkdir(parents=True)

    huge_excerpt = "x" * 5000
    raw_items = [
        {
            "id": "apple-newsroom:launch",
            "source": "apple-newsroom",
            "source_kind": "feed_item",
            "title": "Launch update",
            "excerpt": huge_excerpt,
            "body": huge_excerpt,
            "url": "https://example.com/posts/launch-update",
            "timestamps": {"created_at": "2026-04-20T07:00:00Z"},
            "provenance": {
                "provider": "example.com",
                "acquisition_mode": "rss_poll",
                "authority_tier": "primary",
                "primary_source_url": "https://example.com/posts/launch-update",
            },
        }
    ]
    (raw_directory / "collected-items.json").write_text(json.dumps(raw_items, indent=2) + "\n")

    invocation = StubCodexInvocation("# Codex Digest\n")
    summarizer = CodexCliSummarizer(invocation=invocation)

    summarizer.summarize_archive(archive_directory)

    prompt = invocation.calls[0]["prompt"]
    assert isinstance(prompt, str)
    assert "https://example.com/posts/launch-update" in prompt
    assert '"title": "Launch update"' in prompt
    assert len(prompt) < 5000
    assert huge_excerpt not in prompt



def test_codex_cli_summarizer_requires_raw_collected_items_json(tmp_path: Path) -> None:
    archive_directory = tmp_path / "2026-04-20"
    archive_directory.mkdir(parents=True)

    summarizer = CodexCliSummarizer(invocation=StubCodexInvocation("unused"))

    with pytest.raises(FileNotFoundError):
        summarizer.summarize_archive(archive_directory)
