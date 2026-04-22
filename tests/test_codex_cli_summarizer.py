import json
from pathlib import Path

from hermes_pulse.summarization.codex_cli import build_codex_digest_prompt, build_summary_format_instructions


def test_build_codex_digest_prompt_limits_embedded_raw_items_and_reports_omissions(tmp_path: Path) -> None:
    archive_directory = tmp_path / "archive"
    raw_directory = archive_directory / "raw"
    raw_directory.mkdir(parents=True)
    items = [
        {
            "id": f"item-{index}",
            "source": "test-source",
            "source_kind": "document",
            "title": f"Title {index}",
            "excerpt": "excerpt " + ("x" * 500),
            "body": "body " + ("y" * 500),
            "url": f"https://example.com/{index}",
            "timestamps": {
                "created_at": f"2026-04-21T00:{index:02d}:00Z",
                "updated_at": None,
                "start_at": None,
                "end_at": None,
            },
            "provenance": {
                "provider": "example.com",
                "acquisition_mode": "fixture",
                "authority_tier": "primary",
                "primary_source_url": f"https://example.com/{index}",
                "raw_record_id": f"raw-{index}",
            },
        }
        for index in range(250)
    ]
    raw_items = json.dumps(items, ensure_ascii=False)
    (raw_directory / "collected-items.json").write_text(raw_items)

    prompt = build_codex_digest_prompt(archive_directory, raw_items)

    assert '"title": "Title 0"' in prompt
    primary_grounding = prompt.split("## URL/title index for all URL-bearing items", 1)[0]
    assert '"title": "Title 249"' not in primary_grounding
    assert "## item counts" in prompt
    assert '"included_in_prompt": 200' in prompt
    assert '"omitted_from_prompt": 50' in prompt


def test_build_summary_format_instructions_requires_inline_markdown_links_in_briefing_v1() -> None:
    instructions = build_summary_format_instructions("briefing-v1")

    assert any("文中" in line and "Markdown リンク" in line for line in instructions)
    assert any("URL を文末に列挙しない" in line for line in instructions)


def test_build_codex_digest_prompt_embeds_url_title_index_for_all_url_items(tmp_path: Path) -> None:
    archive_directory = tmp_path / "archive"
    raw_directory = archive_directory / "raw"
    raw_directory.mkdir(parents=True)
    items = [
        {
            "id": f"item-{index}",
            "source": f"source-{index % 3}",
            "source_kind": "document",
            "title": f"Title {index}",
            "url": f"https://example.com/{index}",
        }
        for index in range(250)
    ]
    raw_items = json.dumps(items, ensure_ascii=False)
    (raw_directory / "collected-items.json").write_text(raw_items)

    prompt = build_codex_digest_prompt(archive_directory, raw_items)

    assert "## URL/title index for all URL-bearing items" in prompt
    assert '"url": "https://example.com/0"' in prompt
    assert '"title": "Title 0"' in prompt
    assert '"url": "https://example.com/249"' in prompt
    assert '"title": "Title 249"' in prompt
    url_index = prompt.split("## URL/title index for all URL-bearing items", 1)[1]
    assert '"source"' not in url_index
    assert '"id"' not in url_index


def test_build_codex_digest_prompt_omits_internal_source_labels_from_llm_grounding(tmp_path: Path) -> None:
    archive_directory = tmp_path / "archive"
    raw_directory = archive_directory / "raw"
    raw_directory.mkdir(parents=True)
    raw_items = json.dumps(
        [
            {
                "id": "x-home:1",
                "source": "x_home_timeline_reverse_chronological",
                "source_kind": "social_post",
                "title": "Qwen post",
                "excerpt": "Qwen3.6-27B on timeline",
                "url": "https://x.com/example/status/1",
                "provenance": {"acquisition_mode": "oauth2"},
            },
            {
                "id": "openai-news:1",
                "source": "openai-newsroom",
                "source_kind": "document",
                "title": "OpenAI launch",
                "excerpt": "Launch post",
                "url": "https://openai.com/index/launch",
                "provenance": {"acquisition_mode": "rss_poll"},
            },
        ],
        ensure_ascii=False,
    )
    (raw_directory / "collected-items.json").write_text(raw_items)

    prompt = build_codex_digest_prompt(archive_directory, raw_items)

    assert '"url": "https://x.com/example/status/1"' in prompt
    assert '"url": "https://openai.com/index/launch"' in prompt
    assert '"title": "Qwen post"' in prompt
    assert '"title": "OpenAI launch"' in prompt
    assert "x_home_timeline_reverse_chronological" not in prompt
    assert "openai-newsroom" not in prompt
    assert '"source_kind"' not in prompt
    assert '"provenance"' not in prompt
    assert "raw/collected-items.json" not in prompt
    assert str(archive_directory) not in prompt


def test_build_codex_digest_prompt_fetches_missing_title_for_url_items(tmp_path: Path) -> None:
    archive_directory = tmp_path / "archive"
    raw_directory = archive_directory / "raw"
    raw_directory.mkdir(parents=True)
    raw_items = json.dumps(
        [
            {
                "id": "x-home:1",
                "source": "x_home_timeline_reverse_chronological",
                "source_kind": "social_post",
                "title": None,
                "excerpt": "Timeline excerpt should not become title",
                "url": "https://example.com/missing-title",
            }
        ],
        ensure_ascii=False,
    )
    (raw_directory / "collected-items.json").write_text(raw_items)

    prompt = build_codex_digest_prompt(
        archive_directory,
        raw_items,
        title_fetcher=lambda url: "Fetched title" if url == "https://example.com/missing-title" else None,
    )

    assert '"url": "https://example.com/missing-title"' in prompt
    assert '"title": "Fetched title"' in prompt
    assert "Timeline excerpt should not become title" in prompt


def test_build_codex_digest_prompt_uses_neutral_fallback_title_for_untitled_urls(tmp_path: Path) -> None:
    archive_directory = tmp_path / "archive"
    raw_directory = archive_directory / "raw"
    raw_directory.mkdir(parents=True)
    raw_items = json.dumps(
        [
            {
                "id": "internal:42",
                "source": "x_home_timeline_reverse_chronological",
                "source_kind": "social_post",
                "title": None,
                "excerpt": None,
                "body": None,
                "url": "https://example.com/no-title",
            }
        ],
        ensure_ascii=False,
    )
    (raw_directory / "collected-items.json").write_text(raw_items)

    prompt = build_codex_digest_prompt(
        archive_directory,
        raw_items,
        title_fetcher=lambda _url: None,
    )

    assert '"url": "https://example.com/no-title"' in prompt
    assert '"title": "example.com/no-title"' in prompt
    assert "x_home_timeline_reverse_chronological" not in prompt
    assert "internal:42" not in prompt
