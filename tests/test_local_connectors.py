from pathlib import Path

from hermes_pulse.connectors.grok_history import GrokHistoryConnector
from hermes_pulse.connectors.hermes_history import HermesHistoryConnector
from hermes_pulse.connectors.notes import NotesConnector


def test_hermes_history_connector_normalizes_local_session() -> None:
    connector = HermesHistoryConnector()

    items = connector.collect(Path("fixtures/hermes_history/sample_session.json"))

    assert len(items) == 1
    item = items[0]
    assert item.source == "hermes_history"
    assert item.source_kind == "conversation"
    assert item.title == "Morning planning"
    assert item.provenance is not None
    assert item.provenance.acquisition_mode == "local_store"
    assert item.provenance.provider == "hermes_agent"


def test_notes_connector_normalizes_local_markdown() -> None:
    connector = NotesConnector()

    items = connector.collect(Path("fixtures/notes/sample_notes.md"))

    assert len(items) == 1
    item = items[0]
    assert item.source == "notes"
    assert item.source_kind == "note"
    assert "Call dentist tomorrow morning" in (item.body or "")
    assert item.provenance is not None
    assert item.provenance.acquisition_mode == "local_store"
    assert item.provenance.provider == "notes"


def test_grok_history_connector_normalizes_browser_export() -> None:
    connector = GrokHistoryConnector()

    items = connector.collect(Path("fixtures/grok_history/sample_export"))

    assert len(items) == 1
    item = items[0]
    assert item.id == "conv-1"
    assert item.source == "grok_history"
    assert item.source_kind == "conversation"
    assert item.title == "定期券の経路相談"
    assert "human: 目黒経由と渋谷経由のどちらが得？" in (item.body or "")
    assert "assistant: 乗り換えなしなら目黒連絡が妥当です。" in (item.body or "")
    assert item.provenance is not None
    assert item.provenance.acquisition_mode == "browser_automation_experimental"
    assert item.provenance.provider == "grok"
