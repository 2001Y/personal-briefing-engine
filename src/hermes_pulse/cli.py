import argparse
from collections.abc import Sequence
from pathlib import Path

from hermes_pulse.delivery.local_markdown import LocalMarkdownDelivery
from hermes_pulse.rendering import render_morning_digest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hermes-pulse")
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)

    if args.output is not None:
        markdown = render_morning_digest([], [])
        LocalMarkdownDelivery().deliver(markdown, args.output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
