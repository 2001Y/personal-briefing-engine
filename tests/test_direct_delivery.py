from datetime import date
from pathlib import Path

import pytest

import hermes_pulse.direct_delivery as direct_delivery
from hermes_pulse.summarization.base import SummaryArtifact


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REGISTRY_PATH = ROOT / "fixtures/source_registry/sample_sources.yaml"
FEED_FIXTURE_PATH = ROOT / "fixtures/feed_samples/official_feed.xml"
SEARCH_FIXTURE_PATH = ROOT / "fixtures/search_samples/known_source_results.html"
HERMES_HISTORY_PATH = ROOT / "fixtures/hermes_history/sample_session.json"
CHATGPT_HISTORY_PATH = ROOT / "fixtures/chatgpt_history/sample_export"
GROK_HISTORY_PATH = ROOT / "fixtures/grok_history/sample_export"
NOTES_PATH = ROOT / "fixtures/notes/sample_notes.md"
DEFAULT_CODEX_MODEL = "gpt-5.4"
DEFAULT_SUMMARY_FORMAT = "briefing-v1"
EXPECTED_TITLE = "☀ *Hermes Pulse Morning Briefing*"
EXPECTED_PRIMARY_HEADING = "▫ 主要トピック"
EXPECTED_SCHEDULE_HEADING = "▫ 今日の予定・期限"
EXPECTED_NOTES_HEADING = "▫ 気になるメモ"


def test_post_canonical_digest_to_slack_reads_exact_canonical_artifact(tmp_path: Path) -> None:
    archive_directory = tmp_path / date.today().isoformat()
    digest_path = archive_directory / "summary" / "codex-digest.md"
    digest_path.parent.mkdir(parents=True, exist_ok=True)
    digest_path.write_text("# Codex Digest\n\n- Exact canonical content\n")
    calls: list[dict[str, object]] = []

    def fake_post_message(
        text: str,
        channel: str,
        thread_ts: str | None = None,
        *,
        unfurl_links: bool = False,
        unfurl_media: bool = False,
    ) -> dict[str, object]:
        calls.append(
            {
                "text": text,
                "channel": channel,
                "thread_ts": thread_ts,
                "unfurl_links": unfurl_links,
                "unfurl_media": unfurl_media,
            }
        )
        return {"ok": True, "channel": channel, "ts": "1712345.6789"}

    result = direct_delivery.post_canonical_digest_to_slack(
        archive_directory,
        channel="C123",
        thread_ts="1712345.6789",
        post_message=fake_post_message,
    )

    assert calls == [
        {
            "text": "# Codex Digest\n\n- Exact canonical content\n",
            "channel": "C123",
            "thread_ts": "1712345.6789",
            "unfurl_links": False,
            "unfurl_media": False,
        }
    ]
    assert result.archive_directory == archive_directory
    assert result.digest_path == digest_path
    assert result.content == digest_path.read_text()
    assert result.slack_response == {"ok": True, "channel": "C123", "ts": "1712345.6789"}


def test_post_canonical_digest_to_slack_converts_markdown_links_to_slack_links(tmp_path: Path) -> None:
    archive_directory = tmp_path / date.today().isoformat()
    digest_path = archive_directory / "summary" / "codex-digest.md"
    digest_path.parent.mkdir(parents=True, exist_ok=True)
    digest_path.write_text("# Codex Digest\n\n- [Launch update](https://example.com/posts/launch-update)\n")
    calls: list[dict[str, object]] = []

    def fake_post_message(
        text: str,
        channel: str,
        thread_ts: str | None = None,
        *,
        unfurl_links: bool = False,
        unfurl_media: bool = False,
    ) -> dict[str, object]:
        calls.append(
            {
                "text": text,
                "channel": channel,
                "thread_ts": thread_ts,
                "unfurl_links": unfurl_links,
                "unfurl_media": unfurl_media,
            }
        )
        return {"ok": True, "channel": channel, "ts": "1712345.6789"}

    result = direct_delivery.post_canonical_digest_to_slack(
        archive_directory,
        channel="C123",
        post_message=fake_post_message,
    )

    assert calls == [
        {
            "text": "# Codex Digest\n\n- <https://example.com/posts/launch-update|Launch update>\n",
            "channel": "C123",
            "thread_ts": None,
            "unfurl_links": False,
            "unfurl_media": False,
        }
    ]
    assert result.content == digest_path.read_text()


def test_post_canonical_digest_to_slack_splits_oversized_digest_into_threaded_posts(tmp_path: Path) -> None:
    archive_directory = tmp_path / date.today().isoformat()
    digest_path = archive_directory / "summary" / "codex-digest.md"
    digest_path.parent.mkdir(parents=True, exist_ok=True)
    digest_path.write_text(
        "# Codex Digest\n\n"
        + "\n\n".join(
            f"Paragraph {index}: [Link {index}](https://example.com/{index}) " + ("x" * 90)
            for index in range(1, 7)
        )
        + "\n"
    )
    calls: list[dict[str, object]] = []

    def fake_post_message(
        text: str,
        channel: str,
        thread_ts: str | None = None,
        *,
        unfurl_links: bool = False,
        unfurl_media: bool = False,
    ) -> dict[str, object]:
        calls.append(
            {
                "text": text,
                "channel": channel,
                "thread_ts": thread_ts,
                "unfurl_links": unfurl_links,
                "unfurl_media": unfurl_media,
            }
        )
        return {"ok": True, "channel": channel, "ts": f"1712345.67{len(calls)}"}

    result = direct_delivery.post_canonical_digest_to_slack(
        archive_directory,
        channel="C123",
        post_message=fake_post_message,
        slack_message_limit=180,
    )

    assert len(calls) >= 2
    assert calls[0]["thread_ts"] is None
    assert calls[1]["thread_ts"] == "1712345.671"
    assert all("[Link" not in call["text"] for call in calls)
    assert all("<https://example.com/" in call["text"] for call in calls)
    assert result.slack_response == {"ok": True, "channel": "C123", "ts": f"1712345.67{len(calls)}"}
    assert result.slack_responses == [
        {"ok": True, "channel": "C123", "ts": f"1712345.67{index}"}
        for index in range(1, len(calls) + 1)
    ]
    assert result.posted_messages == [call["text"] for call in calls]


def test_build_parser_uses_hermes_pulse_direct_delivery_program_name() -> None:
    assert direct_delivery.build_parser().prog == "hermes-pulse-direct-delivery"


def test_post_canonical_digest_to_slack_fails_clearly_when_canonical_artifact_is_missing(
    tmp_path: Path,
) -> None:
    archive_directory = tmp_path / date.today().isoformat()

    with pytest.raises(FileNotFoundError, match=r"summary/codex-digest\.md"):
        direct_delivery.post_canonical_digest_to_slack(
            archive_directory,
            channel="C123",
            post_message=lambda *args, **kwargs: {"ok": True},
        )


def test_main_runs_morning_digest_pipeline_and_posts_exact_canonical_digest(
    monkeypatch,
    tmp_path: Path,
) -> None:
    summary_template = "# Codex Digest\n\n- Canonical archive summary\n"
    codex_calls: list[Path] = []

    class StubCodexCliSummarizer:
        def __init__(self, *, model: str = DEFAULT_CODEX_MODEL, summary_format: str = DEFAULT_SUMMARY_FORMAT) -> None:
            assert model == DEFAULT_CODEX_MODEL
            assert summary_format == DEFAULT_SUMMARY_FORMAT

        def summarize_archive(self, archive_directory: str | Path) -> SummaryArtifact:
            archive_directory = Path(archive_directory)
            codex_calls.append(archive_directory)
            output_path = archive_directory / "summary" / "codex-digest.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(summary_template)
            return SummaryArtifact(path=output_path, content="# Returned content that must not be posted\n")

    monkeypatch.setattr(direct_delivery, "CodexCliSummarizer", StubCodexCliSummarizer)
    archive_root = tmp_path / "archive-root"
    archive_date = date.today().isoformat()
    slack_calls: list[dict[str, object]] = []

    def fake_post_message(
        text: str,
        channel: str,
        thread_ts: str | None = None,
        *,
        unfurl_links: bool = False,
        unfurl_media: bool = False,
    ) -> dict[str, object]:
        slack_calls.append(
            {
                "text": text,
                "channel": channel,
                "thread_ts": thread_ts,
                "unfurl_links": unfurl_links,
                "unfurl_media": unfurl_media,
            }
        )
        return {"ok": True, "channel": channel, "ts": "1712345.6789"}

    assert (
        direct_delivery.main(
            [
                "--source-registry",
                str(SOURCE_REGISTRY_PATH),
                "--feed-fixture",
                str(FEED_FIXTURE_PATH),
                "--search-fixture",
                str(SEARCH_FIXTURE_PATH),
                "--hermes-history",
                str(HERMES_HISTORY_PATH),
                "--notes",
                str(NOTES_PATH),
                "--archive-root",
                str(archive_root),
                "--channel",
                "C123",
                "--thread-ts",
                "1712345.6789",
            ],
            post_message=fake_post_message,
        )
        == 0
    )

    archive_directory = archive_root / archive_date
    digest_path = archive_directory / "summary" / "codex-digest.md"

    assert codex_calls == [archive_directory]
    assert digest_path.read_text() == summary_template
    assert slack_calls == [
        {
            "text": summary_template,
            "channel": "C123",
            "thread_ts": "1712345.6789",
            "unfurl_links": False,
            "unfurl_media": False,
        }
    ]


def test_build_parser_accepts_codex_model_and_summary_format() -> None:
    args = direct_delivery.build_parser().parse_args(
        [
            "--channel",
            "D123",
            "--codex-model",
            DEFAULT_CODEX_MODEL,
            "--summary-format",
            DEFAULT_SUMMARY_FORMAT,
        ]
    )

    assert args.codex_model == DEFAULT_CODEX_MODEL
    assert args.summary_format == DEFAULT_SUMMARY_FORMAT
    assert direct_delivery.build_parser().parse_args(["--channel", "D123", "--chatgpt-history", str(CHATGPT_HISTORY_PATH)]).chatgpt_history == CHATGPT_HISTORY_PATH
    assert direct_delivery.build_parser().parse_args(["--channel", "D123", "--grok-history", str(GROK_HISTORY_PATH)]).grok_history == GROK_HISTORY_PATH


def test_briefing_v1_summary_format_instructions_define_requested_headings() -> None:
    instructions = direct_delivery.build_summary_format_instructions(DEFAULT_SUMMARY_FORMAT)

    assert EXPECTED_TITLE in instructions[1]
    assert EXPECTED_PRIMARY_HEADING in instructions[1]
    assert EXPECTED_SCHEDULE_HEADING in instructions[1]
    assert EXPECTED_NOTES_HEADING in instructions[1]


def test_summarize_archive_with_retries_uses_requested_model_and_format() -> None:
    calls: list[dict[str, object]] = []

    class FakeSummarizer:
        def summarize_archive(self, archive_directory: str | Path) -> SummaryArtifact:
            calls.append({"archive_directory": str(archive_directory)})
            return SummaryArtifact(path=Path("/tmp/codex-digest.md"), content="# digest")

    artifact = direct_delivery._summarize_archive_with_retries(
        Path("/tmp/archive"),
        codex_model=DEFAULT_CODEX_MODEL,
        summary_format=DEFAULT_SUMMARY_FORMAT,
        retry_delays_seconds=(),
        summarizer_factory=lambda **kwargs: FakeSummarizer(),
        sleep=lambda _seconds: None,
    )

    assert artifact.content == "# digest"
    assert calls == [{"archive_directory": "/tmp/archive"}]


def test_summarize_archive_with_retries_retries_twice_after_failures() -> None:
    attempts: list[int] = []
    sleeps: list[int] = []

    class FlakySummarizer:
        def summarize_archive(self, archive_directory: str | Path) -> SummaryArtifact:
            attempts.append(len(attempts) + 1)
            if len(attempts) < 3:
                raise RuntimeError("temporary high demand")
            return SummaryArtifact(path=Path("/tmp/codex-digest.md"), content="# ok")

    artifact = direct_delivery._summarize_archive_with_retries(
        Path("/tmp/archive"),
        retry_delays_seconds=(300, 300),
        summarizer_factory=lambda **kwargs: FlakySummarizer(),
        sleep=sleeps.append,
    )

    assert artifact.content == "# ok"
    assert attempts == [1, 2, 3]
    assert sleeps == [300, 300]


def test_summarize_archive_with_retries_raises_after_exhausting_retries() -> None:
    attempts: list[int] = []
    sleeps: list[int] = []

    class AlwaysFailingSummarizer:
        def summarize_archive(self, archive_directory: str | Path) -> SummaryArtifact:
            attempts.append(len(attempts) + 1)
            raise RuntimeError("temporary high demand")

    with pytest.raises(RuntimeError, match="temporary high demand"):
        direct_delivery._summarize_archive_with_retries(
            Path("/tmp/archive"),
            retry_delays_seconds=(300, 300),
            summarizer_factory=lambda **kwargs: AlwaysFailingSummarizer(),
            sleep=sleeps.append,
        )

    assert attempts == [1, 2, 3]
    assert sleeps == [300, 300]
