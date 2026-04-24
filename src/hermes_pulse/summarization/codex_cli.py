import json
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from hermes_pulse.summarization.base import (
    CODEX_DIGEST_RELATIVE_PATH,
    RAW_ITEMS_RELATIVE_PATH,
    CodexInvocation,
    SummaryArtifact,
)
from hermes_pulse.title_resolution import fetch_title_from_url, synthesize_title_with_codex_spark

DEFAULT_CODEX_TIMEOUT_SECONDS = 900
DEFAULT_CODEX_MODEL = "gpt-5.4"
DEFAULT_SUMMARY_FORMAT = "briefing-v1"
MAX_PROMPT_RAW_ITEMS = 50


class CodexCliSummarizer:
    def __init__(
        self,
        invocation: CodexInvocation | None = None,
        *,
        model: str = DEFAULT_CODEX_MODEL,
        summary_format: str = DEFAULT_SUMMARY_FORMAT,
        title_fetcher=None,
        title_synthesizer=None,
    ) -> None:
        self._invocation = invocation or CodexCliInvocation(model=model)
        self._summary_format = summary_format
        self._title_fetcher = title_fetcher or fetch_title_from_url
        self._title_synthesizer = title_synthesizer or synthesize_title_with_codex_spark

    def summarize_archive(self, archive_directory: str | Path) -> SummaryArtifact:
        archive_directory = Path(archive_directory)
        raw_items_path = archive_directory / RAW_ITEMS_RELATIVE_PATH
        raw_items = raw_items_path.read_text()
        items = json.loads(raw_items)
        chunks = _chunk_items(items, MAX_PROMPT_RAW_ITEMS)
        with tempfile.TemporaryDirectory(prefix="hermes-pulse-codex-") as temp_dir:
            codex_context = Path(temp_dir)
            _stage_sanitized_codex_context(archive_directory, codex_context)
            partial_summaries: list[str] = []
            for chunk_index, chunk in enumerate(chunks, start=1):
                prompt = build_codex_digest_prompt(
                    archive_directory,
                    json.dumps(chunk, ensure_ascii=False),
                    summary_format=self._summary_format,
                    title_fetcher=self._title_fetcher,
                    title_synthesizer=self._title_synthesizer,
                    chunk_index=chunk_index,
                    chunk_total=len(chunks),
                )
                partial_summaries.append(self._invocation.run(prompt, cwd=codex_context))
            if len(partial_summaries) == 1:
                content = partial_summaries[0]
            else:
                merge_prompt = build_codex_merge_prompt(partial_summaries, summary_format=self._summary_format)
                content = self._invocation.run(merge_prompt, cwd=codex_context)

        output_path = archive_directory / CODEX_DIGEST_RELATIVE_PATH
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)
        return SummaryArtifact(
            path=output_path,
            content=content,
            partial_contents=partial_summaries if len(partial_summaries) > 1 else None,
        )


class CodexCliInvocation:
    def __init__(
        self,
        executable: str = "codex",
        *,
        model: str = DEFAULT_CODEX_MODEL,
        timeout_seconds: int = DEFAULT_CODEX_TIMEOUT_SECONDS,
    ) -> None:
        self._executable = executable
        self._model = model
        self._timeout_seconds = timeout_seconds

    def run(self, prompt: str, *, cwd: Path) -> str:
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".md") as output_file:
            try:
                completed = subprocess.run(
                    [
                        self._executable,
                        "exec",
                        "--model",
                        self._model,
                        "--cd",
                        str(cwd),
                        "--skip-git-repo-check",
                        "--ephemeral",
                        "--output-last-message",
                        output_file.name,
                        "-",
                    ],
                    input=prompt,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=self._timeout_seconds,
                )
            except subprocess.TimeoutExpired as error:
                timeout_seconds = int(error.timeout) if error.timeout else self._timeout_seconds
                raise RuntimeError(f"codex exec timed out after {timeout_seconds}s") from error
            if completed.returncode != 0:
                raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "codex exec failed")
            return Path(output_file.name).read_text()


def build_codex_digest_prompt(
    archive_directory: Path,
    raw_items: str,
    *,
    summary_format: str = DEFAULT_SUMMARY_FORMAT,
    title_fetcher=None,
    title_synthesizer=None,
    chunk_index: int = 1,
    chunk_total: int = 1,
) -> str:
    prepared_raw_items = json.dumps(_prepare_items_for_prompt(json.loads(raw_items)), ensure_ascii=False)
    compact_raw_items, raw_item_counts = _compact_raw_items_for_prompt(
        prepared_raw_items,
        title_fetcher=title_fetcher,
        title_synthesizer=title_synthesizer,
    )
    lines = [
        "あなたは Hermes Pulse の要約担当です。",
        "以下の sanitized archive context から canonical digest を作成してください。",
        "出力は日本語の Markdown のみを返してください。前置きや説明は不要です。",
        "一次情報としてこの prompt に埋め込まれた sanitized grounding を最優先で根拠にしてください。",
        "本文中のリンクは可能な限り保持し、URL を壊さないでください。",
        "不明な点は断定せず、与えられた情報だけで簡潔に要約してください。",
        "内部的な source 名や流入元ラベルではなく、見えている内容そのものを同列に扱ってください。",
        f"この prompt は収集差分 chunk {chunk_index}/{chunk_total} です。chunk 内の重要事項を取りこぼさず要約してください。",
        "",
        *build_summary_format_instructions(summary_format),
        "",
        "## item counts",
        "```json",
        json.dumps(raw_item_counts, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Primary grounding: normalized content snapshot",
        "```json",
        compact_raw_items.rstrip(),
        "```",
        "",
    ]
    return "\n".join(lines)


def build_codex_merge_prompt(chunk_summaries: list[str], *, summary_format: str = DEFAULT_SUMMARY_FORMAT) -> str:
    lines = [
        "あなたは Hermes Pulse の最終編集担当です。",
        "以下は複数 chunk から作った部分要約です。重要事項を重複なく統合し、最終版だけを返してください。",
        "情報量を落としすぎず、同一テーマの重複 bullet は統合してください。",
        "",
        *build_summary_format_instructions(summary_format),
        "",
    ]
    for index, summary in enumerate(chunk_summaries, start=1):
        lines.extend(
            [
                f"## Partial summary {index}",
                summary.rstrip(),
                "",
            ]
        )
    return "\n".join(lines)


def _stage_sanitized_codex_context(archive_directory: Path, codex_context: Path) -> None:
    codex_context.mkdir(parents=True, exist_ok=True)


def build_summary_format_instructions(summary_format: str) -> list[str]:
    if summary_format == "briefing-v1":
        return [
            "出力フォーマットは briefing-v1 を厳守してください。",
            "見出しはこの順番で固定してください: `☀ *Hermes Pulse Morning Briefing*` / `▫ 主要トピック` / `▫ 今日の予定・期限`。",
            "リンクが必要な箇所は、該当する語句を Markdown リンク `[ラベル](URL)` として文中に埋め込んでください。",
            "URL を文末に列挙しないでください。裸の URL を単独で並べるのも避けてください。",
            "`▫ 主要トピック` は必要な件数だけ箇条書きにしてよい。重要事項の取りこぼしを避け、各項目は 1 行で要点→必要なら文中リンク。",
            "`▫ 主要トピック` は internal source 名に引きずられず、与えられた URL/title/本文断片を同列に見て重要度順に選んでください。",
            "`▫ 今日の予定・期限` は当日または近い日時の予定だけを書く。無ければ `- 目立った予定なし`。",
        ]
    raise ValueError(f"Unsupported summary format: {summary_format}")


def _chunk_items(items: list[dict[str, object]], chunk_size: int) -> list[list[dict[str, object]]]:
    if not items:
        return [[]]
    return [items[index : index + chunk_size] for index in range(0, len(items), chunk_size)]


def _compact_raw_items_for_prompt(raw_items: str, *, title_fetcher=None, title_synthesizer=None) -> tuple[str, dict[str, int]]:
    items = json.loads(raw_items)
    compact_items: list[dict[str, object]] = []
    fetcher = title_fetcher or fetch_title_from_url
    synthesizer = title_synthesizer or synthesize_title_with_codex_spark
    for item in items[:MAX_PROMPT_RAW_ITEMS]:
        timestamps = item.get("timestamps") or {}
        compact_items.append(
            {
                "title": _resolve_item_title(item, fetcher=fetcher, synthesizer=synthesizer),
                "excerpt": _truncate_text(item.get("excerpt"), max_length=280),
                "body": _truncate_text(item.get("body"), max_length=280),
                "url": item.get("url"),
                "timestamps": {
                    "created_at": timestamps.get("created_at"),
                    "updated_at": timestamps.get("updated_at"),
                    "start_at": timestamps.get("start_at"),
                    "end_at": timestamps.get("end_at"),
                },
            }
        )
    raw_item_counts = {
        "total_items": len(items),
        "included_in_prompt": len(compact_items),
        "omitted_from_prompt": max(len(items) - len(compact_items), 0),
    }
    return json.dumps(compact_items, ensure_ascii=False, indent=2) + "\n", raw_item_counts


def _prepare_items_for_prompt(items: list[dict[str, object]]) -> list[dict[str, object]]:
    deduped_items = _dedupe_items_by_url(items)
    return _order_items_for_prompt(deduped_items)


def _dedupe_items_by_url(items: list[dict[str, object]]) -> list[dict[str, object]]:
    deduped_by_url: dict[str, dict[str, object]] = {}
    passthrough: list[dict[str, object]] = []
    for item in items:
        url = item.get("url")
        if not isinstance(url, str) or not url:
            passthrough.append(item)
            continue
        existing = deduped_by_url.get(url)
        if existing is None or _item_text_weight(item) > _item_text_weight(existing):
            deduped_by_url[url] = item
    return passthrough + list(deduped_by_url.values())


def _order_items_for_prompt(items: list[dict[str, object]]) -> list[dict[str, object]]:
    if len(items) <= 1:
        return items
    indexed_items = list(enumerate(items))
    clusters: list[dict[str, object]] = []
    for index, item in indexed_items:
        signature = _item_signature(item)
        placed = False
        for cluster in clusters:
            cluster_signature = cluster["signature"]
            if isinstance(cluster_signature, set) and len(signature & cluster_signature) >= 1:
                cluster_items = cluster["items"]
                if isinstance(cluster_items, list):
                    cluster_items.append((index, item))
                cluster_signature.update(signature)
                placed = True
                break
        if not placed:
            clusters.append({"signature": set(signature), "items": [(index, item)]})
    ordered: list[dict[str, object]] = []
    for cluster in clusters:
        cluster_items = cluster["items"]
        if isinstance(cluster_items, list):
            cluster_items.sort(key=lambda value: value[0])
            ordered.extend(item for _, item in cluster_items)
    return ordered


def _item_signature(item: dict[str, object]) -> set[str]:
    tokens: set[str] = set()
    stopwords = {"item", "items", "update", "updates", "note", "notes", "news", "launch", "launches", "ships", "ship", "first", "second", "third"}
    url = item.get("url")
    if isinstance(url, str) and url:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if host and host != "example.com":
            tokens.add(f"host:{host}")
        for token in re.findall(r"[A-Za-z0-9]{3,}", parsed.path.lower()):
            if not token.isdigit() and token not in stopwords:
                tokens.add(f"path:{token}")
    for field_name in ("title", "excerpt", "body"):
        value = item.get(field_name)
        if not isinstance(value, str):
            continue
        for token in re.findall(r"[A-Za-z0-9]{3,}", value.lower()):
            if not token.isdigit() and token not in stopwords:
                tokens.add(token)
    return tokens


def _item_text_weight(item: dict[str, object]) -> int:
    score = 0
    for field_name in ("title", "excerpt", "body"):
        value = item.get(field_name)
        if isinstance(value, str):
            score += len(value)
    return score


def _resolve_item_title(item: dict[str, object], *, fetcher, synthesizer) -> str | None:
    existing_title = _truncate_text(item.get("title"))
    if existing_title is not None:
        return existing_title
    url = item.get("url")
    if isinstance(url, str) and url:
        fetched_title = _truncate_text(fetcher(url))
        if fetched_title is not None:
            return fetched_title
        body_text = _truncate_text(item.get("body"), max_length=280) or _truncate_text(item.get("excerpt"), max_length=280)
        if body_text:
            synthesized_title = _truncate_text(synthesizer(body_text, url))
            if synthesized_title is not None:
                return synthesized_title
        return _fallback_title_for_url_item(url)
    return _truncate_text(item.get("excerpt")) or _truncate_text(item.get("body")) or "Untitled item"


def _truncate_text(value: object, *, max_length: int = 160) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 1]}…"


def _fallback_title_for_url_item(url: str) -> str:
    return url.split("//", 1)[-1]
