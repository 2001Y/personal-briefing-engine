import argparse
import json
from collections.abc import Callable, Sequence
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from hermes_pulse.archive import write_morning_digest_archive
from hermes_pulse.collection import collect_for_trigger
from hermes_pulse.connectors.audit_context import AuditContextConnector, load_audit_context_fixture
from hermes_pulse.connectors.feed_registry import FeedRegistryConnector
from hermes_pulse.connectors.gmail import GmailConnector
from hermes_pulse.connectors.google_calendar import GoogleCalendarConnector
from hermes_pulse.connectors.hermes_history import HermesHistoryConnector
from hermes_pulse.connectors.known_source_search import KnownSourceSearchConnector
from hermes_pulse.connectors.location_context import LocationContextConnector, load_location_context_fixture
from hermes_pulse.connectors.notes import NotesConnector
from hermes_pulse.connectors.x_url import XUrlConnector
from hermes_pulse.db import (
    get_approval_action,
    list_active_suppression_subjects,
    record_approval_action,
    record_delivery,
    record_feedback,
    record_suppression,
    record_trigger_run,
    update_approval_action,
    update_trigger_run_status,
    upsert_connector_cursor,
    upsert_source_registry_state,
)
from hermes_pulse.delivery.local_markdown import LocalMarkdownDelivery
from hermes_pulse.models import CollectedItem, SourceRegistryEntry, TriggerEvent, TriggerScope
from hermes_pulse.rendering import (
    _parse_key_value_lines,
    render_feed_update_nudge,
    render_feed_update_deep_brief,
    render_feed_update_source_audit,
    render_gap_window_mini_digest,
    render_leave_now_warning,
    render_location_arrival_mini_digest,
    render_mail_operational_warning,
    render_shopping_replenishment_action_prep,
    render_trigger_quality_review,
)
from hermes_pulse.source_registry import load_source_registry
from hermes_pulse.summarization import CodexCliSummarizer
from hermes_pulse.trigger_registry import get_trigger_profile


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_REGISTRY = REPO_ROOT / "fixtures/source_registry/default_sources.yaml"


class BoundConnector:
    def __init__(self, collector: Callable[[], list[object]]) -> None:
        self._collector = collector

    def collect(self) -> list[object]:
        return self._collector()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hermes-pulse")
    parser.add_argument(
        "command",
        nargs="?",
        choices=(
            "morning-digest",
            "evening-digest",
            "leave-now-warning",
            "mail-operational",
            "shopping-replenishment",
            "feed-update",
            "location-arrival",
            "review-trigger-quality",
            "gap-window-mini-digest",
            "feed-update-deep-brief",
            "feed-update-source-audit",
            "approve-action",
            "reject-action",
            "complete-action",
            "failed-action",
        ),
    )
    parser.add_argument("--source-registry", type=Path)
    parser.add_argument("--feed-fixture", type=Path)
    parser.add_argument("--search-fixture", type=Path)
    parser.add_argument("--calendar-fixture", type=Path)
    parser.add_argument("--gmail-fixture", type=Path)
    parser.add_argument("--location-fixture", type=Path)
    parser.add_argument("--audit-fixture", type=Path)
    parser.add_argument("--hermes-history", type=Path)
    parser.add_argument("--notes", type=Path)
    parser.add_argument("--archive-root", type=Path)
    parser.add_argument("--state-db", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--action-id")
    parser.add_argument("--now")
    parser.add_argument("--x-signals")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command is None:
        return 0

    run_id: str | None = None
    profile = None
    occurred_at = _occurred_at_for_command(args.command, args)
    if args.command in {"approve-action", "reject-action", "complete-action", "failed-action"}:
        if args.state_db is None or not args.action_id:
            raise ValueError("action update commands require --state-db and --action-id")
        _update_approval_action_from_command(args.state_db, action_id=args.action_id, command=args.command, occurred_at=occurred_at)
        return 0
    if args.state_db is not None:
        profile = _profile_for_command(args.command)
        run_id = record_trigger_run(
            args.state_db,
            event_type=profile.event_type,
            profile_id=profile.id,
            occurred_at=occurred_at,
            output_mode=profile.output_mode,
            status="started",
        )

    delivery_succeeded = False
    pending_connector_cursor_update: tuple[list[CollectedItem], list[str], str] | None = None
    pending_source_registry_state_update: tuple[list[SourceRegistryEntry], list[CollectedItem], str] | None = None
    pending_suppression_update: tuple[list[CollectedItem], str, str, str] | None = None
    pending_feedback_update: tuple[list[CollectedItem], str, str] | None = None
    pending_approval_action_update: tuple[list[CollectedItem], str, str] | None = None
    try:
        markdown: str | None = None

        if args.command in {"morning-digest", "evening-digest"}:
            items = _build_digest(args.command, args)
            occurred_at = _occurred_at_for_command(args.command, args)
            deliverable_items = items
            if args.state_db is not None:
                deliverable_items = _filter_suppressed_items(
                    args.state_db,
                    items=items,
                    trigger_family=profile.event_type,
                    occurred_at=occurred_at,
                )
                pending_connector_cursor_update = (
                    items,
                    _parse_x_signal_types(getattr(args, "x_signals", None)),
                    occurred_at,
                )
                pending_source_registry_state_update = (
                    load_source_registry(args.source_registry or DEFAULT_SOURCE_REGISTRY),
                    items,
                    occurred_at,
                )
                if run_id is not None:
                    pending_suppression_update = (deliverable_items, profile.event_type, occurred_at, run_id)
            archive_root = args.archive_root or Path.home() / "Pulse"
            archive_directory = write_morning_digest_archive(
                items=deliverable_items,
                archive_root=archive_root,
                archive_date=date.today().isoformat(),
            )
            markdown = CodexCliSummarizer().summarize_archive(archive_directory).content
        elif args.command == "leave-now-warning":
            markdown = _build_leave_now_warning(args)
        elif args.command == "mail-operational":
            markdown = _build_mail_operational(args)
        elif args.command == "shopping-replenishment":
            items = _build_event_trigger_items("shopping.replenishment.default", args)
            markdown = render_shopping_replenishment_action_prep(items)
            if args.state_db is not None and run_id is not None:
                pending_approval_action_update = (items, occurred_at, run_id)
        elif args.command == "feed-update":
            markdown = _build_feed_update(args)
        elif args.command == "location-arrival":
            markdown = _build_location_arrival(args)
        elif args.command == "review-trigger-quality":
            items = _build_event_trigger_items("review.trigger_quality.default", args)
            markdown = render_trigger_quality_review(items)
            if args.state_db is not None and run_id is not None:
                pending_feedback_update = (items, occurred_at, run_id)
        elif args.command == "gap-window-mini-digest":
            markdown = _build_gap_window(args)
        elif args.command == "feed-update-deep-brief":
            markdown = _build_feed_update_deep_brief(args)
        elif args.command == "feed-update-source-audit":
            markdown = _build_feed_update_source_audit(args)
        else:
            return 0

        if args.output is not None and markdown is not None:
            delivered_path = LocalMarkdownDelivery().deliver(markdown, args.output)
            delivery_succeeded = True
            if args.state_db is not None and run_id is not None:
                record_delivery(args.state_db, run_id=run_id, destination=str(delivered_path), status="success")
                if pending_suppression_update is not None:
                    items, trigger_family, occurred_at, suppression_run_id = pending_suppression_update
                    _record_suppression_history(
                        args.state_db,
                        items=items,
                        trigger_family=trigger_family,
                        occurred_at=occurred_at,
                        run_id=suppression_run_id,
                    )

        if args.state_db is not None and pending_source_registry_state_update is not None:
            source_registry, items, occurred_at = pending_source_registry_state_update
            _record_source_registry_state(
                args.state_db,
                source_registry=source_registry,
                items=items,
                occurred_at=occurred_at,
            )

        if args.state_db is not None and pending_feedback_update is not None:
            items, occurred_at, feedback_run_id = pending_feedback_update
            _record_feedback_from_audit_items(
                args.state_db,
                items=items,
                occurred_at=occurred_at,
                run_id=feedback_run_id,
            )

        if args.state_db is not None and pending_approval_action_update is not None:
            items, occurred_at, action_run_id = pending_approval_action_update
            _record_approval_actions_from_items(
                args.state_db,
                items=items,
                occurred_at=occurred_at,
                run_id=action_run_id,
            )

        if args.state_db is not None and pending_connector_cursor_update is not None:
            items, x_signal_types, occurred_at = pending_connector_cursor_update
            _record_connector_cursors_from_items(
                args.state_db,
                items=items,
                occurred_at=occurred_at,
                x_signal_types=x_signal_types,
            )
    except Exception:
        if args.state_db is not None and run_id is not None:
            try:
                if delivery_succeeded:
                    update_trigger_run_status(args.state_db, run_id=run_id, status="delivery_state_error")
                else:
                    update_trigger_run_status(args.state_db, run_id=run_id, status="failed")
            except Exception:
                pass
        raise

    if args.state_db is not None and run_id is not None:
        try:
            update_trigger_run_status(args.state_db, run_id=run_id, status="completed")
        except Exception:
            if delivery_succeeded:
                try:
                    update_trigger_run_status(args.state_db, run_id=run_id, status="delivery_state_error")
                except Exception:
                    pass
            raise
    return 0


def _build_morning_digest(args: argparse.Namespace) -> list[CollectedItem]:
    return _build_digest("morning-digest", args)


def _profile_for_command(command: str | None):
    if command is None:
        raise ValueError("command is required for state recording")
    profile_id = {
        "morning-digest": "digest.morning.default",
        "evening-digest": "digest.evening.default",
        "leave-now-warning": "calendar.leave_now.default",
        "mail-operational": "mail.operational.default",
        "shopping-replenishment": "shopping.replenishment.default",
        "feed-update": "feed.update.default",
        "location-arrival": "location.arrival.default",
        "review-trigger-quality": "review.trigger_quality.default",
        "gap-window-mini-digest": "calendar.gap_window.default",
        "feed-update-deep-brief": "feed.update.expert_depth",
        "feed-update-source-audit": "feed.update.source_audit",
    }[command]
    return get_trigger_profile(profile_id)


def _occurred_at_for_command(command: str | None, args: argparse.Namespace) -> str:
    if args.now:
        return args.now
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_x_signal_types(value: str | None) -> list[str]:
    if not value:
        return []
    return [signal_type.strip() for signal_type in value.split(",") if signal_type.strip()]


def _x_source_for_signal_type(signal_type: str) -> str:
    return {
        "bookmarks": "x_bookmarks",
        "likes": "x_likes",
        "home_timeline_reverse_chronological": "x_home_timeline_reverse_chronological",
    }[signal_type]


def _cursor_sort_key(raw_record_id: str) -> tuple[int, int | str]:
    if raw_record_id.isdigit():
        return (1, int(raw_record_id))
    return (0, raw_record_id)


def _record_connector_cursors_from_items(
    path: Path,
    *,
    items: list[CollectedItem],
    occurred_at: str,
    x_signal_types: list[str],
) -> None:
    top_cursors: dict[str, str | None] = {
        _x_source_for_signal_type(signal_type): None for signal_type in x_signal_types
    }
    for item in items:
        if item.source not in top_cursors:
            continue
        raw_record_id = item.provenance.raw_record_id if item.provenance is not None else None
        if raw_record_id is None:
            continue
        current_cursor = top_cursors[item.source]
        if current_cursor is None or _cursor_sort_key(raw_record_id) > _cursor_sort_key(current_cursor):
            top_cursors[item.source] = raw_record_id

    for connector_id, cursor in top_cursors.items():
        upsert_connector_cursor(
            path,
            connector_id=connector_id,
            cursor=cursor,
            last_poll_at=occurred_at,
            last_success_at=occurred_at,
        )


def _record_source_registry_state(path: Path, *, source_registry: list[SourceRegistryEntry], items: list[CollectedItem], occurred_at: str) -> None:
    item_ids_by_source: dict[str, list[str]] = {}
    for item in items:
        item_ids_by_source.setdefault(item.source, []).append(item.id)

    for entry in source_registry:
        if entry.acquisition_mode not in {"rss_poll", "atom_poll", "known_source_search"}:
            continue
        if entry.id not in item_ids_by_source:
            continue
        upsert_source_registry_state(
            path,
            registry_id=entry.id,
            last_poll_at=occurred_at,
            last_seen_item_ids=json.dumps(item_ids_by_source.get(entry.id, [])),
            last_promoted_item_ids=json.dumps(item_ids_by_source.get(entry.id, [])),
            authority_tier=entry.authority_tier,
        )


def _filter_suppressed_items(path: Path, *, items: list[CollectedItem], trigger_family: str, occurred_at: str) -> list[CollectedItem]:
    suppressed_subjects = list_active_suppression_subjects(
        path,
        trigger_family=trigger_family,
        occurred_at=occurred_at,
    )
    if not suppressed_subjects:
        return items
    return [item for item in items if json.dumps([item.source, item.id]) not in suppressed_subjects]


def _record_suppression_history(path: Path, *, items: list[CollectedItem], trigger_family: str, occurred_at: str, run_id: str) -> None:
    cooldown_expires_at = (
        _parse_timestamp(occurred_at) + timedelta(days=1)
    ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    for item in items:
        record_suppression(
            path,
            run_id=run_id,
            subject=json.dumps([item.source, item.id]),
            trigger_family=trigger_family,
            reason="already_delivered_in_same_trigger_family",
            cooldown_expires_at=cooldown_expires_at,
            dismissal_status="active",
            superseded_by_higher_authority=False,
        )


def _record_feedback_from_audit_items(path: Path, *, items: list[CollectedItem], occurred_at: str, run_id: str) -> None:
    for item in items:
        if item.source != "audit_context":
            continue
        metadata = item.metadata
        for signal in ("notification_rate", "ignored_rate", "delivery_failures"):
            value = metadata.get(signal)
            if value is None:
                continue
            record_feedback(
                path,
                run_id=run_id,
                category="trigger_quality",
                subject="review.trigger_quality",
                signal=signal,
                value=str(value),
                recorded_at=occurred_at,
            )
        for subject in metadata.get("late_triggers", []):
            record_feedback(
                path,
                run_id=run_id,
                category="trigger_quality",
                subject=str(subject),
                signal="late_trigger",
                value="1",
                recorded_at=occurred_at,
            )
        for subject in metadata.get("weak_sources", []):
            record_feedback(
                path,
                run_id=run_id,
                category="source_quality",
                subject=str(subject),
                signal="weak_source",
                value="1",
                recorded_at=occurred_at,
            )


def _record_approval_actions_from_items(path: Path, *, items: list[CollectedItem], occurred_at: str, run_id: str) -> None:
    item = next(iter(items), None)
    if item is None:
        return
    fields = _parse_key_value_lines(item.body or "")
    subject = json.dumps(
        {
            "buy": fields.get("buy") or item.title or item.id,
            "preferred_store": fields.get("preferred store"),
            "link": fields.get("link"),
        },
        ensure_ascii=False,
    )
    record_approval_action(
        path,
        run_id=run_id,
        action_kind="shopping.replenishment",
        subject=subject,
        approval_boundary_reached=True,
        user_decision="pending",
        execution_result="not_executed",
        recorded_at=occurred_at,
    )


def _update_approval_action_from_command(path: Path, *, action_id: str, command: str, occurred_at: str) -> None:
    action = get_approval_action(path, action_id=action_id)
    if action is None:
        raise ValueError("approval action not found")
    user_decision, execution_result = action
    if command in {"complete-action", "failed-action"}:
        if user_decision != "approved" or execution_result != "approved_pending_execution":
            raise ValueError("approval action is not awaiting execution completion")
        updated_execution_result = "executed" if command == "complete-action" else "failed"
        update_approval_action(
            path,
            action_id=action_id,
            user_decision="approved",
            execution_result=updated_execution_result,
            recorded_at=occurred_at,
        )
        return
    if user_decision != "pending":
        raise ValueError("approval action is not pending")
    if command == "approve-action":
        update_approval_action(
            path,
            action_id=action_id,
            user_decision="approved",
            execution_result="approved_pending_execution",
            recorded_at=occurred_at,
        )
        return
    if command == "reject-action":
        update_approval_action(
            path,
            action_id=action_id,
            user_decision="rejected",
            execution_result="cancelled",
            recorded_at=occurred_at,
        )
        return
    raise ValueError(f"unsupported action update command: {command}")


def _build_leave_now_warning(args: argparse.Namespace) -> str | None:
    items = _build_event_trigger_items("calendar.leave_now.default", args)
    return render_leave_now_warning(items, now=_parse_timestamp(args.now) if args.now else datetime.now(timezone.utc))


def _build_mail_operational(args: argparse.Namespace) -> str | None:
    items = _build_event_trigger_items("mail.operational.default", args)
    return render_mail_operational_warning(items)


def _build_shopping_replenishment(args: argparse.Namespace) -> str | None:
    items = _build_event_trigger_items("shopping.replenishment.default", args)
    return render_shopping_replenishment_action_prep(items)


def _build_feed_update(args: argparse.Namespace) -> str | None:
    items = _build_event_trigger_items("feed.update.default", args)
    return render_feed_update_nudge(items)


def _build_location_arrival(args: argparse.Namespace) -> str | None:
    items = _build_event_trigger_items("location.arrival.default", args)
    return render_location_arrival_mini_digest(items)


def _build_review_trigger_quality(args: argparse.Namespace) -> str | None:
    items = _build_event_trigger_items("review.trigger_quality.default", args)
    return render_trigger_quality_review(items)


def _build_gap_window(args: argparse.Namespace) -> str | None:
    items = _build_event_trigger_items("calendar.gap_window.default", args)
    now = _parse_timestamp(args.now) if args.now else datetime.now(timezone.utc)
    return render_gap_window_mini_digest(items, now=now)


def _build_feed_update_deep_brief(args: argparse.Namespace) -> str | None:
    items = _build_event_trigger_items("feed.update.expert_depth", args)
    return render_feed_update_deep_brief(items)


def _build_feed_update_source_audit(args: argparse.Namespace) -> str | None:
    items = _build_event_trigger_items("feed.update.source_audit", args)
    return render_feed_update_source_audit(items)


def _build_event_trigger_items(profile_id: str, args: argparse.Namespace) -> list[CollectedItem]:
    profile = get_trigger_profile(profile_id)
    source_registry = load_source_registry(args.source_registry or DEFAULT_SOURCE_REGISTRY)
    feed_fetcher = _build_feed_fetcher(getattr(args, "feed_fixture", None))
    search_fetcher = _build_feed_fetcher(getattr(args, "search_fixture", None))
    calendar_fixture = getattr(args, "calendar_fixture", None)
    gmail_fixture = getattr(args, "gmail_fixture", None)
    location_fixture = getattr(args, "location_fixture", None)
    audit_fixture = getattr(args, "audit_fixture", None)
    notes_path = getattr(args, "notes", None)
    calendar_runner = _build_json_runner(calendar_fixture)
    gmail_runner = _build_json_runner(gmail_fixture)
    occurred_at = (getattr(args, "now", None) or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"))
    trigger = TriggerEvent(
        id=f"event:{profile.id}",
        type=profile.event_type,
        profile_id=profile.id,
        occurred_at=occurred_at,
        scope=TriggerScope(),
    )
    connectors = {
        "feed_registry": BoundConnector(
            lambda: FeedRegistryConnector(fetcher=feed_fetcher).collect(source_registry)
        ),
        "known_source_search": BoundConnector(
            lambda: KnownSourceSearchConnector(fetcher=search_fetcher).collect(source_registry)
        ),
    }
    if calendar_runner is not None:
        connectors["google_calendar"] = BoundConnector(lambda: GoogleCalendarConnector(runner=calendar_runner).collect())
    if gmail_runner is not None:
        connectors["gmail"] = BoundConnector(lambda: GmailConnector(runner=gmail_runner).collect())
    if notes_path is not None:
        connectors["notes"] = BoundConnector(lambda: NotesConnector().collect(notes_path))
    if location_fixture is not None:
        connectors["location_context"] = BoundConnector(
            lambda: LocationContextConnector(runner=lambda: load_location_context_fixture(location_fixture)).collect()
        )
    if audit_fixture is not None:
        connectors["audit_context"] = BoundConnector(
            lambda: AuditContextConnector(runner=lambda: load_audit_context_fixture(audit_fixture)).collect()
        )
    return collect_for_trigger(trigger, profile, connectors)


def _build_digest(command: str, args: argparse.Namespace) -> list[CollectedItem]:
    profile_id = {
        "morning-digest": "digest.morning.default",
        "evening-digest": "digest.evening.default",
    }[command]
    profile = get_trigger_profile(profile_id)
    source_registry = load_source_registry(args.source_registry or DEFAULT_SOURCE_REGISTRY)
    feed_fetcher = _build_feed_fetcher(args.feed_fixture)
    search_fetcher = _build_feed_fetcher(args.search_fixture)
    calendar_fixture = getattr(args, "calendar_fixture", None)
    gmail_fixture = getattr(args, "gmail_fixture", None)
    calendar_runner = _build_json_runner(calendar_fixture)
    gmail_runner = _build_json_runner(gmail_fixture)
    occurred_at = (getattr(args, "now", None) or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"))
    trigger = TriggerEvent(
        id="scheduled:digest.morning.default",
        type=profile.event_type,
        profile_id=profile.id,
        occurred_at=occurred_at,
        scope=TriggerScope(),
    )
    connectors = {
        "feed_registry": BoundConnector(
            lambda: FeedRegistryConnector(fetcher=feed_fetcher).collect(source_registry)
        ),
        "known_source_search": BoundConnector(
            lambda: KnownSourceSearchConnector(fetcher=search_fetcher).collect(source_registry)
        ),
    }
    if calendar_runner is not None:
        connectors["google_calendar"] = BoundConnector(lambda: GoogleCalendarConnector(runner=calendar_runner).collect())
    if gmail_runner is not None:
        connectors["gmail"] = BoundConnector(lambda: GmailConnector(runner=gmail_runner).collect())
    if args.x_signals:
        signal_types = [value.strip() for value in args.x_signals.split(",") if value.strip()]
        connectors["x_signals"] = BoundConnector(lambda: XUrlConnector().collect(signal_types))
    if args.hermes_history is not None:
        connectors["hermes_history"] = BoundConnector(
            lambda: HermesHistoryConnector().collect(args.hermes_history)
        )
    if args.notes is not None:
        connectors["notes"] = BoundConnector(lambda: NotesConnector().collect(args.notes))
    return collect_for_trigger(trigger, profile, connectors)


def _build_feed_fetcher(feed_fixture: Path | None) -> Callable[[str], str] | None:
    if feed_fixture is None:
        return None
    payload = feed_fixture.read_text()
    return lambda url: payload


def _build_json_runner(path: Path | None) -> Callable[[], list[dict[str, object]]] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text())
    return lambda: payload


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


if __name__ == "__main__":
    raise SystemExit(main())
