import json
import subprocess
from collections.abc import Callable, Sequence
from typing import Any


Runner = Callable[[str, str], dict[str, Any]]

from hermes_pulse.models import CitationLink, CollectedItem, IntentSignals, ItemTimestamps, Provenance


SignalType = str
_REQUEST_FIELDS = "tweet.fields=created_at,author_id,text"
_SIGNAL_PATHS: dict[SignalType, tuple[str, str]] = {
    "bookmarks": ("x_bookmarks", "/2/users/{user_id}/bookmarks?max_results=100&" + _REQUEST_FIELDS),
    "likes": ("x_likes", "/2/users/{user_id}/liked_tweets?max_results=100&" + _REQUEST_FIELDS),
    "home_timeline_reverse_chronological": (
        "x_home_timeline_reverse_chronological",
        "/2/users/{user_id}/timelines/reverse_chronological?max_results=100&" + _REQUEST_FIELDS,
    ),
}


class XUrlConnector:
    id = "x_signals"
    source_family = "x"

    def __init__(self, runner: Runner | None = None) -> None:
        self._runner = runner or _run_xurl_json

    def collect(self, signal_types: Sequence[str]) -> list[CollectedItem]:
        unsupported = [signal_type for signal_type in signal_types if signal_type not in _SIGNAL_PATHS]
        if unsupported:
            raise ValueError(f"Unsupported X signal type: {unsupported[0]}")

        if not signal_types:
            return []

        auth_type, me_payload = self._resolve_auth("/2/users/me")
        me = me_payload.get("data") or {}
        user_id = me.get("id")
        if not user_id:
            raise ValueError("xurl /2/users/me did not return a user id")

        items: list[CollectedItem] = []
        for signal_type in signal_types:
            source, path_template = _SIGNAL_PATHS[signal_type]
            payload = self._runner(path_template.format(user_id=user_id), auth_type)
            items.extend(_parse_items(source, signal_type, payload))
        return items

    def _resolve_auth(self, path: str) -> tuple[str, dict[str, Any]]:
        last_error: Exception | None = None
        for auth_type in ("oauth2", "oauth1"):
            try:
                return auth_type, self._runner(path, auth_type)
            except Exception as exc:
                last_error = exc
        assert last_error is not None
        raise last_error


def _parse_items(source: str, signal_type: str, payload: dict[str, Any]) -> list[CollectedItem]:
    users = {
        user.get("id"): user
        for user in ((payload.get("includes") or {}).get("users") or [])
        if user.get("id")
    }
    items: list[CollectedItem] = []
    for record in payload.get("data") or []:
        tweet_id = record["id"]
        text = record.get("text") or ""
        author = users.get(record.get("author_id"), {})
        username = author.get("username")
        url = f"https://x.com/{username}/status/{tweet_id}" if username else f"https://x.com/i/web/status/{tweet_id}"
        intent = IntentSignals(saved=signal_type == "bookmarks", liked=signal_type == "likes")
        items.append(
            CollectedItem(
                id=f"{source}:{tweet_id}",
                source=source,
                source_kind="post",
                title=_title_from_text(text),
                excerpt=text,
                body=text,
                url=url,
                timestamps=ItemTimestamps(created_at=record.get("created_at")),
                intent_signals=intent,
                provenance=Provenance(
                    provider="x.com",
                    acquisition_mode="official_api",
                    authority_tier="primary",
                    primary_source_url=url,
                    raw_record_id=tweet_id,
                ),
                citation_chain=[CitationLink(label=_title_from_text(text), url=url, relation="primary")],
                metadata={
                    "x_signal": signal_type,
                    "author_id": record.get("author_id"),
                    "author_username": username,
                },
            )
        )
    return items


def _title_from_text(text: str) -> str:
    compact = " ".join(text.split())
    return compact[:80] if compact else "X post"


def _run_xurl_json(path: str, auth_type: str) -> dict[str, Any]:
    result = subprocess.run(
        ["xurl", "--auth", auth_type, path],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)
