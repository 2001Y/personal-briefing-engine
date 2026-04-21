import json
from pathlib import Path
from typing import Any

from hermes_pulse.models import CitationLink, CollectedItem, ItemTimestamps, Provenance


class ChatGPTHistoryConnector:
    id = "chatgpt_history"
    source_family = "local_context"

    def collect(self, path: str | Path) -> list[CollectedItem]:
        base = Path(path)
        conversations_path = _resolve_export_file(base, "conversations.json")
        if conversations_path is None:
            return []
        payload = json.loads(conversations_path.read_text())
        if not isinstance(payload, list):
            raise ValueError("ChatGPT conversations export must be a list")
        account = _resolve_account(base)
        items: list[CollectedItem] = []
        for conversation in payload:
            if not isinstance(conversation, dict):
                continue
            conversation_id = conversation.get("id")
            if not conversation_id:
                continue
            lines = _serialize_conversation_lines(conversation)
            title = conversation.get("title") or "ChatGPT conversation"
            url = f"https://chatgpt.com/c/{conversation_id}"
            items.append(
                CollectedItem(
                    id=str(conversation_id),
                    source="chatgpt_history",
                    source_kind="conversation",
                    title=title,
                    body="\n\n".join(lines) or None,
                    url=url,
                    timestamps=ItemTimestamps(
                        created_at=_normalize_timestamp(conversation.get("create_time")),
                        updated_at=_normalize_timestamp(conversation.get("update_time")),
                    ),
                    provenance=Provenance(
                        provider="chatgpt",
                        acquisition_mode="official_export",
                        authority_tier="primary",
                        primary_source_url=url,
                        raw_record_id=str(conversation_id),
                    ),
                    citation_chain=[CitationLink(label=title, url=url, relation="primary")],
                    metadata={
                        "account": account,
                        "message_count": len(lines),
                    },
                )
            )
        return items


def _resolve_account(base: Path) -> str | None:
    manifest_path = _resolve_export_file(base, "manifest.json")
    if manifest_path is not None:
        try:
            payload = json.loads(manifest_path.read_text())
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            account = payload.get("account")
            if isinstance(account, str) and account:
                return account
    user_path = _resolve_export_file(base, "user.json")
    if user_path is None:
        return None
    payload = json.loads(user_path.read_text())
    if not isinstance(payload, dict):
        return None
    account = payload.get("email")
    return account if isinstance(account, str) and account else None


def _resolve_export_file(base: Path, filename: str) -> Path | None:
    candidates = [
        base / filename,
        base / "extracted" / filename,
        base / "extracted" / "conversations" / filename,
        base / "conversations" / filename,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    for candidate in base.rglob(filename):
        if candidate.is_file():
            return candidate
    return None


def _serialize_conversation_lines(conversation: dict[str, Any]) -> list[str]:
    mapping = conversation.get("mapping")
    if not isinstance(mapping, dict):
        return []
    sortable_messages: list[tuple[float, int, str, str]] = []
    for index, node in enumerate(mapping.values()):
        if not isinstance(node, dict):
            continue
        message = node.get("message")
        if not isinstance(message, dict):
            continue
        author = message.get("author") or {}
        role = author.get("role") if isinstance(author, dict) else None
        if not isinstance(role, str) or not role:
            continue
        text = _extract_message_text(message.get("content"))
        if not text:
            continue
        timestamp = message.get("create_time")
        if not isinstance(timestamp, (int, float)):
            timestamp = node.get("create_time")
        sortable_messages.append((_sortable_timestamp(timestamp), index, role.lower(), text))
    sortable_messages.sort(key=lambda value: (value[0], value[1]))
    return [f"{role}: {text}" for _, _, role, text in sortable_messages]


def _extract_message_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, dict):
        return ""
    parts = content.get("parts")
    if isinstance(parts, list):
        values = [part.strip() for part in parts if isinstance(part, str) and part.strip()]
        if values:
            return "\n\n".join(values)
    text = content.get("text")
    if isinstance(text, str):
        return text.strip()
    if isinstance(text, dict):
        value = text.get("value")
        if isinstance(value, str):
            return value.strip()
    return ""


def _sortable_timestamp(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return float("inf")


def _normalize_timestamp(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    return None
