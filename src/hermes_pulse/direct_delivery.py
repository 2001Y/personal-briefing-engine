import argparse
import importlib.util
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Protocol

from hermes_pulse.archive import write_morning_digest_archive
from hermes_pulse.cli import _build_morning_digest
from hermes_pulse.summarization import CodexCliSummarizer
from hermes_pulse.summarization.base import CODEX_DIGEST_RELATIVE_PATH


DEFAULT_SLACK_DIRECT_PATH = Path.home() / ".hermes" / "scripts" / "slack_direct.py"
DEFAULT_SLACK_MESSAGE_LIMIT = 3500
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")


class SlackPoster(Protocol):
    def __call__(
        self,
        text: str,
        channel: str,
        thread_ts: str | None = None,
        *,
        unfurl_links: bool = False,
        unfurl_media: bool = False,
    ) -> Any:
        ...


@dataclass(frozen=True)
class DirectDeliveryResult:
    archive_directory: Path
    digest_path: Path
    content: str
    posted_messages: list[str]
    slack_response: Any
    slack_responses: list[Any]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hermes-pulse-direct-delivery")
    parser.add_argument("--source-registry", type=Path)
    parser.add_argument("--feed-fixture", type=Path)
    parser.add_argument("--search-fixture", type=Path)
    parser.add_argument("--calendar-fixture", type=Path)
    parser.add_argument("--gmail-fixture", type=Path)
    parser.add_argument("--hermes-history", type=Path)
    parser.add_argument("--notes", type=Path)
    parser.add_argument("--archive-root", type=Path)
    parser.add_argument("--x-signals")
    parser.add_argument("--channel", required=True)
    parser.add_argument("--thread-ts")
    return parser


def main(argv: Sequence[str] | None = None, *, post_message: SlackPoster | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    run_morning_digest_direct_delivery(args, post_message=post_message)
    return 0


def run_morning_digest_direct_delivery(
    args: argparse.Namespace,
    *,
    post_message: SlackPoster | None = None,
) -> DirectDeliveryResult:
    items = _build_morning_digest(args)
    archive_root = args.archive_root or Path.home() / "Pulse"
    archive_directory = write_morning_digest_archive(
        items=items,
        archive_root=archive_root,
        archive_date=date.today().isoformat(),
    )
    CodexCliSummarizer().summarize_archive(archive_directory)
    return post_canonical_digest_to_slack(
        archive_directory,
        channel=args.channel,
        thread_ts=args.thread_ts,
        post_message=post_message,
    )


def post_canonical_digest_to_slack(
    archive_directory: str | Path,
    *,
    channel: str,
    thread_ts: str | None = None,
    post_message: SlackPoster | None = None,
    slack_message_limit: int = DEFAULT_SLACK_MESSAGE_LIMIT,
) -> DirectDeliveryResult:
    archive_directory = Path(archive_directory)
    digest_path = archive_directory / CODEX_DIGEST_RELATIVE_PATH
    if not digest_path.exists():
        raise FileNotFoundError(f"Canonical Codex digest artifact is missing: {digest_path}")

    content = digest_path.read_text()
    rendered_content = _render_digest_for_slack(content)
    message_chunks = _split_slack_text(rendered_content, limit=slack_message_limit)
    poster = post_message or load_slack_direct_post_message()
    slack_responses = _post_slack_chunks(
        poster,
        message_chunks,
        channel=channel,
        thread_ts=thread_ts,
    )
    slack_response = slack_responses[-1]
    return DirectDeliveryResult(
        archive_directory=archive_directory,
        digest_path=digest_path,
        content=content,
        posted_messages=message_chunks,
        slack_response=slack_response,
        slack_responses=slack_responses,
    )


def load_slack_direct_post_message(script_path: str | Path = DEFAULT_SLACK_DIRECT_PATH) -> SlackPoster:
    script_path = Path(script_path)
    if not script_path.exists():
        raise FileNotFoundError(f"Slack direct poster script is missing: {script_path}")

    spec = importlib.util.spec_from_file_location("hermes_pulse_slack_direct", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load Slack direct poster script: {script_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    post_message = getattr(module, "post_message", None)
    if not callable(post_message):
        raise RuntimeError(f"Slack direct poster script does not define callable post_message: {script_path}")
    return post_message


def _render_digest_for_slack(markdown: str) -> str:
    return MARKDOWN_LINK_RE.sub(lambda match: f"<{match.group(2)}|{match.group(1)}>", markdown)


def _split_slack_text(text: str, *, limit: int = DEFAULT_SLACK_MESSAGE_LIMIT) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        split_at = remaining.rfind("\n\n", 0, limit + 1)
        separator_length = 2
        if split_at == -1:
            split_at = remaining.rfind("\n", 0, limit + 1)
            separator_length = 1
        if split_at == -1 or split_at < limit // 2:
            split_at = limit
            separator_length = 0
        chunk = remaining[:split_at].rstrip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_at + separator_length :].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks or [text]


def _post_slack_chunks(
    poster: SlackPoster,
    chunks: list[str],
    *,
    channel: str,
    thread_ts: str | None,
) -> list[Any]:
    responses: list[Any] = []
    active_thread_ts = thread_ts
    for index, chunk in enumerate(chunks):
        response = poster(
            chunk,
            channel,
            thread_ts=active_thread_ts,
            unfurl_links=False,
            unfurl_media=False,
        )
        responses.append(response)
        if index == 0 and active_thread_ts is None:
            response_ts = response.get("ts") if isinstance(response, dict) else None
            if isinstance(response_ts, str) and response_ts:
                active_thread_ts = response_ts
    return responses


if __name__ == "__main__":
    raise SystemExit(main())
