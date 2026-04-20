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
                last_promoted_item_ids = COALESCE(excluded.last_promoted_item_ids, source_registry_state.last_promoted_item_ids),
                authority_tier = excluded.authority_tier,
                notes = COALESCE(excluded.notes, source_registry_state.notes)
            """,
            (registry_id, last_poll_at, last_seen_item_ids, last_promoted_item_ids, authority_tier, notes),
        )
        connection.commit()
