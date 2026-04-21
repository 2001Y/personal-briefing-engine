import json
from pathlib import Path

from hermes_pulse.models import CollectedItem, ItemTimestamps, Provenance


class GrokHistoryConnector:
    id = "grok_history"
    source_family = "local_context"

    def collect(self, path: str | Path) -> list[CollectedItem]:
        base = Path(path)
        payload = json.loads((base / "conversations.index.json").read_text())
        conversations = payload.get("conversations", [])
        items: list[CollectedItem] = []
        for conversation in conversations:
            conversation_id = conversation.get("conversationId") or conversation.get("id")
            if not conversation_id:
                continue
            responses_path = base / "responses" / f"{conversation_id}.responses.json"
            body = None
            response_count = 0
            if responses_path.exists():
                responses_payload = json.loads(responses_path.read_text())
                response_lines = []
                for response in responses_payload.get("responses", []):
                    message = (response.get("message") or "").strip()
                    if not message:
                        continue
                    sender = str(response.get("sender") or "unknown").lower()
                    if sender == "assistant":
                        sender = "assistant"
                    response_lines.append(f"{sender}: {message}")
                response_count = len(responses_payload.get("responses", []))
                body = "\n\n".join(response_lines) or None
            items.append(
                CollectedItem(
                    id=conversation_id,
                    source="grok_history",
                    source_kind="conversation",
                    title=conversation.get("title"),
                    body=body,
                    timestamps=ItemTimestamps(
                        created_at=conversation.get("createTime"),
                        updated_at=conversation.get("modifyTime"),
                    ),
                    provenance=Provenance(
                        provider="grok",
                        acquisition_mode="browser_automation_experimental",
                        raw_record_id=conversation_id,
                    ),
                    metadata={
                        "response_count": response_count,
                    },
                )
            )
        return items
