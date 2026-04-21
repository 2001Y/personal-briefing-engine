import json
from pathlib import Path

import hermes_pulse.cli
from hermes_pulse.exporters.grok_browser_export import GrokBrowserExporter


class FakeRunner:
    def __init__(self) -> None:
        self.page_tokens: list[str | None] = []
        self.response_ids: list[str] = []

    def fetch_conversations(self, *, page_size: int, page_token: str | None = None) -> dict[str, object]:
        self.page_tokens.append(page_token)
        if page_token is None:
            return {
                "conversations": [
                    {"conversationId": "conv-1", "title": "定期券の経路相談"},
                ],
                "nextPageToken": "page-2",
            }
        assert page_token == "page-2"
        return {
            "conversations": [
                {"conversationId": "conv-2", "title": "旅行計画"},
            ]
        }

    def fetch_responses(self, conversation_id: str) -> dict[str, object]:
        self.response_ids.append(conversation_id)
        return {
            "responses": [
                {"sender": "human", "message": f"question for {conversation_id}"},
                {"sender": "assistant", "message": f"answer for {conversation_id}"},
            ]
        }


def test_grok_browser_exporter_writes_index_responses_and_manifest(tmp_path: Path) -> None:
    runner = FakeRunner()

    result = GrokBrowserExporter(runner=runner).export(tmp_path, page_size=100)

    index_payload = json.loads((tmp_path / "conversations.index.json").read_text())
    responses_one = json.loads((tmp_path / "responses" / "conv-1.responses.json").read_text())
    responses_two = json.loads((tmp_path / "responses" / "conv-2.responses.json").read_text())
    export_result = json.loads((tmp_path / "responses.export.result.json").read_text())
    manifest = json.loads((tmp_path / "manifest.json").read_text())

    assert runner.page_tokens == [None, "page-2"]
    assert runner.response_ids == ["conv-1", "conv-2"]
    assert [item["conversationId"] for item in index_payload["conversations"]] == ["conv-1", "conv-2"]
    assert responses_one["responses"][0]["message"] == "question for conv-1"
    assert responses_two["responses"][1]["message"] == "answer for conv-2"
    assert export_result["conversation_count"] == 2
    assert export_result["response_files_total"] == 2
    assert export_result["failure_count"] == 0
    assert result["failure_count"] == 0
    assert manifest["provider"] == "grok"
    assert manifest["acquisition_mode"] == "browser_automation_experimental"


def test_refresh_grok_history_command_invokes_exporter(monkeypatch, tmp_path: Path) -> None:
    calls: list[dict[str, object]] = []

    class FakeExporter:
        def __init__(self, *, cdp_port: int = 9223, runner=None) -> None:
            calls.append({"cdp_port": cdp_port, "runner": runner, "event": "init"})

        def export(self, output_dir: str | Path, *, page_size: int = 100) -> dict[str, object]:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "manifest.json").write_text("{}")
            calls.append({"output_dir": output_dir, "page_size": page_size, "event": "export"})
            return {"output_dir": str(output_dir), "conversation_count": 0, "response_files_total": 0, "failure_count": 0}

    monkeypatch.setattr(hermes_pulse.cli, "GrokBrowserExporter", FakeExporter)
    output_dir = tmp_path / "grok-export"

    assert (
        hermes_pulse.cli.main(
            [
                "refresh-grok-history",
                "--output-dir",
                str(output_dir),
                "--cdp-port",
                "9223",
                "--page-size",
                "50",
            ]
        )
        == 0
    )

    assert calls == [
        {"cdp_port": 9223, "runner": None, "event": "init"},
        {"output_dir": output_dir, "page_size": 50, "event": "export"},
    ]
