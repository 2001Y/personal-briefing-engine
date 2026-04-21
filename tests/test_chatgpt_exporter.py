import json
import zipfile
from pathlib import Path

import hermes_pulse.cli
from hermes_pulse.connectors.chatgpt_history import ChatGPTHistoryConnector
from hermes_pulse.exporters.chatgpt_export_prep import ChatGPTExportPreparer


def _build_nested_chatgpt_export(tmp_path: Path) -> Path:
    source_dir = tmp_path / "source"
    inner_dir = source_dir / "inner"
    inner_dir.mkdir(parents=True)
    (inner_dir / "conversations.json").write_text(
        json.dumps(
            [
                {
                    "id": "chatcmpl-conv-1",
                    "title": "旅行計画の相談",
                    "create_time": 1713600000.0,
                    "update_time": 1713600300.0,
                    "mapping": {},
                }
            ]
        )
    )
    (inner_dir / "user.json").write_text(json.dumps({"email": "mail+chatgpt@tam.nz"}))
    (inner_dir / "export_manifest.json").write_text(json.dumps({"export_id": "exp-1"}))

    inner_zip = source_dir / "Conversations.zip"
    with zipfile.ZipFile(inner_zip, "w") as archive:
        archive.write(inner_dir / "conversations.json", arcname="conversations.json")
        archive.write(inner_dir / "user.json", arcname="user.json")
        archive.write(inner_dir / "export_manifest.json", arcname="export_manifest.json")

    outer_zip = tmp_path / "OpenAI-export.zip"
    with zipfile.ZipFile(outer_zip, "w") as archive:
        archive.writestr("report.html", "<html></html>")
        archive.write(inner_zip, arcname="User Online Activity/Conversations__sample-chatgpt-0001.zip")
    return outer_zip


def test_chatgpt_export_preparer_extracts_nested_zip_and_writes_manifest(tmp_path: Path) -> None:
    outer_zip = _build_nested_chatgpt_export(tmp_path)
    output_dir = tmp_path / "prepared"

    result = ChatGPTExportPreparer().prepare(outer_zip, output_dir)

    conversations = json.loads((output_dir / "extracted" / "conversations" / "conversations.json").read_text())
    user_payload = json.loads((output_dir / "extracted" / "conversations" / "user.json").read_text())
    manifest = json.loads((output_dir / "manifest.json").read_text())

    assert conversations[0]["id"] == "chatcmpl-conv-1"
    assert user_payload["email"] == "mail+chatgpt@tam.nz"
    assert manifest["provider"] == "chatgpt"
    assert manifest["acquisition_mode"] == "official_export"
    assert manifest["conversation_count"] == 1
    assert manifest["account"] == "mail+chatgpt@tam.nz"
    assert result["conversation_count"] == 1
    assert ChatGPTHistoryConnector().collect(output_dir)[0].id == "chatcmpl-conv-1"


def test_prepare_chatgpt_history_command_invokes_preparer(monkeypatch, tmp_path: Path) -> None:
    calls: list[dict[str, object]] = []

    class FakePreparer:
        def prepare(self, input_path: str | Path, output_dir: str | Path) -> dict[str, object]:
            input_path = Path(input_path)
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "manifest.json").write_text("{}")
            calls.append({"input_path": input_path, "output_dir": output_dir})
            return {"conversation_count": 0}

    monkeypatch.setattr(hermes_pulse.cli, "ChatGPTExportPreparer", lambda: FakePreparer())
    input_path = tmp_path / "OpenAI-export.zip"
    input_path.write_text("placeholder")
    output_dir = tmp_path / "prepared"

    assert (
        hermes_pulse.cli.main(
            [
                "prepare-chatgpt-history",
                "--input-file",
                str(input_path),
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )

    assert calls == [{"input_path": input_path, "output_dir": output_dir}]
