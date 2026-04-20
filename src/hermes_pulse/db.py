import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS trigger_runs (
        run_id TEXT PRIMARY KEY,
        event_type TEXT NOT NULL,
        profile_id TEXT NOT NULL,
        occurred_at TEXT NOT NULL,
        output_mode TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS connector_cursors (
        connector_id TEXT PRIMARY KEY,
        cursor TEXT,
        last_poll_at TEXT,
        last_success_at TEXT,
        last_error TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS source_registry_state (
        registry_id TEXT PRIMARY KEY,
        last_poll_at TEXT,
        last_seen_item_ids TEXT,
        last_promoted_item_ids TEXT,
        authority_tier TEXT,
        notes TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS deliveries (
        delivery_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        destination TEXT NOT NULL,
        delivered_at TEXT NOT NULL,
        status TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS suppression_history (
        suppression_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        subject TEXT NOT NULL,
        trigger_family TEXT NOT NULL,
        reason TEXT NOT NULL,
        cooldown_expires_at TEXT,
        dismissal_status TEXT NOT NULL,
        superseded_by_higher_authority INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS feedback_log (
        feedback_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        category TEXT NOT NULL,
        subject TEXT NOT NULL,
        signal TEXT NOT NULL,
        value TEXT NOT NULL,
        recorded_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS approval_action_log (
        action_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        action_kind TEXT NOT NULL,
        subject TEXT NOT NULL,
        approval_boundary_reached INTEGER NOT NULL,
        user_decision TEXT NOT NULL,
        execution_result TEXT NOT NULL,
        recorded_at TEXT NOT NULL
    )
    """,
)


def initialize_database(path: str | Path) -> None:
    database_path = Path(path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
        connection.commit()


def record_trigger_run(
    path: str | Path,
    *,
    event_type: str,
    profile_id: str,
    occurred_at: str,
    output_mode: str | None,
    status: str,
) -> str:
    database_path = Path(path)
    initialize_database(database_path)
    run_id = uuid4().hex
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO trigger_runs (run_id, event_type, profile_id, occurred_at, output_mode, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (run_id, event_type, profile_id, occurred_at, output_mode, status, created_at),
        )
        connection.commit()
    return run_id


def record_delivery(
    path: str | Path,
    *,
    run_id: str,
    destination: str,
    status: str,
) -> str:
    database_path = Path(path)
    initialize_database(database_path)
    delivery_id = uuid4().hex
    delivered_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO deliveries (delivery_id, run_id, destination, delivered_at, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (delivery_id, run_id, destination, delivered_at, status),
        )
        connection.commit()
    return delivery_id


def update_trigger_run_status(path: str | Path, *, run_id: str, status: str) -> None:
    database_path = Path(path)
    initialize_database(database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE trigger_runs SET status = ? WHERE run_id = ?",
            (status, run_id),
        )
        connection.commit()


def upsert_connector_cursor(
    path: str | Path,
    *,
    connector_id: str,
    cursor: str | None,
    last_poll_at: str | None,
    last_success_at: str | None,
    last_error: str | None = None,
) -> None:
    database_path = Path(path)
    initialize_database(database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO connector_cursors (connector_id, cursor, last_poll_at, last_success_at, last_error)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(connector_id) DO UPDATE SET
                cursor = COALESCE(excluded.cursor, connector_cursors.cursor),
                last_poll_at = excluded.last_poll_at,
                last_success_at = excluded.last_success_at,
                last_error = excluded.last_error
            """,
            (connector_id, cursor, last_poll_at, last_success_at, last_error),
        )
        connection.commit()


def upsert_source_registry_state(
    path: str | Path,
    *,
    registry_id: str,
    last_poll_at: str | None,
    last_seen_item_ids: str | None,
    last_promoted_item_ids: str | None,
    authority_tier: str | None,
    notes: str | None = None,
) -> None:
    database_path = Path(path)
    initialize_database(database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO source_registry_state (
                registry_id,
                last_poll_at,
                last_seen_item_ids,
                last_promoted_item_ids,
                authority_tier,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(registry_id) DO UPDATE SET
                last_poll_at = excluded.last_poll_at,
                last_seen_item_ids = excluded.last_seen_item_ids,
                last_promoted_item_ids = excluded.last_promoted_item_ids,
                authority_tier = excluded.authority_tier,
                notes = COALESCE(excluded.notes, source_registry_state.notes)
            """,
            (registry_id, last_poll_at, last_seen_item_ids, last_promoted_item_ids, authority_tier, notes),
        )
        connection.commit()


def record_suppression(
    path: str | Path,
    *,
    run_id: str,
    subject: str,
    trigger_family: str,
    reason: str,
    cooldown_expires_at: str | None,
    dismissal_status: str,
    superseded_by_higher_authority: bool,
) -> str:
    database_path = Path(path)
    initialize_database(database_path)
    suppression_id = uuid4().hex
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO suppression_history (
                suppression_id,
                run_id,
                subject,
                trigger_family,
                reason,
                cooldown_expires_at,
                dismissal_status,
                superseded_by_higher_authority
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                suppression_id,
                run_id,
                subject,
                trigger_family,
                reason,
                cooldown_expires_at,
                dismissal_status,
                1 if superseded_by_higher_authority else 0,
            ),
        )
        connection.commit()
    return suppression_id


def list_active_suppression_subjects(
    path: str | Path,
    *,
    trigger_family: str,
    occurred_at: str,
) -> set[str]:
    database_path = Path(path)
    initialize_database(database_path)
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT subject
            FROM suppression_history
            WHERE trigger_family = ?
              AND dismissal_status = 'active'
              AND superseded_by_higher_authority = 0
              AND (cooldown_expires_at IS NULL OR cooldown_expires_at >= ?)
            """,
            (trigger_family, occurred_at),
        ).fetchall()
    return {row[0] for row in rows}


def record_feedback(
    path: str | Path,
    *,
    run_id: str,
    category: str,
    subject: str,
    signal: str,
    value: str,
    recorded_at: str,
) -> str:
    database_path = Path(path)
    initialize_database(database_path)
    feedback_id = uuid4().hex
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO feedback_log (
                feedback_id,
                run_id,
                category,
                subject,
                signal,
                value,
                recorded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (feedback_id, run_id, category, subject, signal, value, recorded_at),
        )
        connection.commit()
    return feedback_id


def record_approval_action(
    path: str | Path,
    *,
    run_id: str,
    action_kind: str,
    subject: str,
    approval_boundary_reached: bool,
    user_decision: str,
    execution_result: str,
    recorded_at: str,
) -> str:
    database_path = Path(path)
    initialize_database(database_path)
    action_id = uuid4().hex
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO approval_action_log (
                action_id,
                run_id,
                action_kind,
                subject,
                approval_boundary_reached,
                user_decision,
                execution_result,
                recorded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action_id,
                run_id,
                action_kind,
                subject,
                1 if approval_boundary_reached else 0,
                user_decision,
                execution_result,
                recorded_at,
            ),
        )
        connection.commit()
    return action_id


def update_approval_action(
    path: str | Path,
    *,
    action_id: str,
    user_decision: str,
    execution_result: str,
    recorded_at: str,
) -> None:
    database_path = Path(path)
    initialize_database(database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            UPDATE approval_action_log
            SET user_decision = ?, execution_result = ?, recorded_at = ?
            WHERE action_id = ?
            """,
            (user_decision, execution_result, recorded_at, action_id),
        )
        connection.commit()


def get_approval_action(path: str | Path, *, action_id: str) -> tuple[str, str] | None:
    database_path = Path(path)
    initialize_database(database_path)
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT user_decision, execution_result FROM approval_action_log WHERE action_id = ?",
            (action_id,),
        ).fetchone()
    if row is None:
        return None
    return (row[0], row[1])
