import sqlite3
from pathlib import Path

from hermes_pulse.db import initialize_database


EXPECTED_TABLES = {
    "trigger_runs",
    "connector_cursors",
    "source_registry_state",
    "deliveries",
    "suppression_history",
    "feedback_log",
    "approval_action_log",
}


def test_initialize_database_creates_minimal_schema(tmp_path: Path) -> None:
    database_path = tmp_path / "hermes-pulse.db"

    initialize_database(database_path)

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert EXPECTED_TABLES <= tables


def test_initialize_database_adds_execution_details_column_to_approval_action_log(tmp_path: Path) -> None:
    database_path = tmp_path / "hermes-pulse.db"

    initialize_database(database_path)

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(approval_action_log)")
        }

    assert "execution_details" in columns
