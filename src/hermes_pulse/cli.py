import argparse
from collections.abc import Callable, Sequence
from pathlib import Path

from hermes_pulse.collection import collect_for_trigger
from hermes_pulse.connectors.feed_registry import FeedRegistryConnector
from hermes_pulse.connectors.hermes_history import HermesHistoryConnector
from hermes_pulse.connectors.notes import NotesConnector
from hermes_pulse.delivery.local_markdown import LocalMarkdownDelivery
from hermes_pulse.models import TriggerEvent, TriggerScope
from hermes_pulse.rendering import render_morning_digest
from hermes_pulse.source_registry import load_source_registry
from hermes_pulse.synthesis import synthesize_candidates
from hermes_pulse.trigger_registry import get_trigger_profile


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_REGISTRY = REPO_ROOT / "fixtures/source_registry/sample_sources.yaml"
DEFAULT_FEED_FIXTURE = REPO_ROOT / "fixtures/feed_samples/official_feed.xml"
DEFAULT_HERMES_HISTORY = REPO_ROOT / "fixtures/hermes_history/sample_session.json"
DEFAULT_NOTES = REPO_ROOT / "fixtures/notes/sample_notes.md"


class BoundConnector:
    def __init__(self, collector: Callable[[], list[object]]) -> None:
        self._collector = collector

    def collect(self) -> list[object]:
        return self._collector()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hermes-pulse")
    parser.add_argument("command", nargs="?", choices=("morning-digest",))
    parser.add_argument("--source-registry", type=Path)
    parser.add_argument("--feed-fixture", type=Path, default=DEFAULT_FEED_FIXTURE)
    parser.add_argument("--hermes-history", type=Path, default=DEFAULT_HERMES_HISTORY)
    parser.add_argument("--notes", type=Path, default=DEFAULT_NOTES)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)

    if args.command == "morning-digest":
        markdown = _build_fixture_backed_morning_digest(args)
    elif args.output is not None:
        markdown = render_morning_digest([], [])
    else:
        return 0

    if args.output is not None:
        LocalMarkdownDelivery().deliver(markdown, args.output)

    return 0


def _build_fixture_backed_morning_digest(args: argparse.Namespace) -> str:
    profile = get_trigger_profile("digest.morning.default")
    source_registry = load_source_registry(args.source_registry or DEFAULT_SOURCE_REGISTRY)
    feed_fixture = args.feed_fixture.read_text()
    trigger = TriggerEvent(
        id="scheduled:digest.morning.default",
        type=profile.event_type,
        profile_id=profile.id,
        occurred_at="2026-04-20T08:00:00Z",
        scope=TriggerScope(),
    )
    connectors = {
        "feed_registry": BoundConnector(
            lambda: FeedRegistryConnector(fetcher=lambda url: feed_fixture).collect(source_registry)
        ),
        "hermes_history": BoundConnector(lambda: HermesHistoryConnector().collect(args.hermes_history)),
        "notes": BoundConnector(lambda: NotesConnector().collect(args.notes)),
    }
    items = collect_for_trigger(trigger, profile, connectors)
    candidates = synthesize_candidates(items)
    return render_morning_digest(candidates, items)


if __name__ == "__main__":
    raise SystemExit(main())
