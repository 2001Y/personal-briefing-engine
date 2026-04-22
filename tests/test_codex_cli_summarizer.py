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

    assert "item-0" in prompt
    primary_grounding = prompt.split("## URL/title index for all URL-bearing items", 1)[0]
    assert "item-249" not in primary_grounding
    assert "raw item counts" in prompt
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
