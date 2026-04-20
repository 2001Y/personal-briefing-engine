import argparse
import importlib.util
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
    slack_response: Any


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-pulse-direct-delivery")
    parser.add_argument("--source-registry", type=Path)
    parser.add_argument("--feed-fixture", type=Path)
    parser.add_argument("--search-fixture", type=Path)
    parser.add_argument("--calendar-fixture", type=Path)
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
) -> DirectDeliveryResult:
    archive_directory = Path(archive_directory)
    digest_path = archive_directory / CODEX_DIGEST_RELATIVE_PATH
    if not digest_path.exists():
        raise FileNotFoundError(f"Canonical Codex digest artifact is missing: {digest_path}")

    content = digest_path.read_text()
    poster = post_message or load_slack_direct_post_message()
    slack_response = poster(
        content,
        channel,
        thread_ts=thread_ts,
        unfurl_links=False,
        unfurl_media=False,
    )
    return DirectDeliveryResult(
        archive_directory=archive_directory,
        digest_path=digest_path,
        content=content,
        slack_response=slack_response,
    )


def load_slack_direct_post_message(script_path: str | Path = DEFAULT_SLACK_DIRECT_PATH) -> SlackPoster:
    script_path = Path(script_path)
    if not script_path.exists():
        raise FileNotFoundError(f"Slack direct poster script is missing: {script_path}")

    spec = importlib.util.spec_from_file_location("codex_pulse_slack_direct", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load Slack direct poster script: {script_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    post_message = getattr(module, "post_message", None)
    if not callable(post_message):
        raise RuntimeError(f"Slack direct poster script does not define callable post_message: {script_path}")
    return post_message


if __name__ == "__main__":
    raise SystemExit(main())
