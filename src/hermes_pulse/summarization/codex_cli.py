import json
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

DEFAULT_CODEX_TIMEOUT_SECONDS = 900

from hermes_pulse.summarization.base import (
    CODEX_DIGEST_RELATIVE_PATH,
    RAW_ITEMS_RELATIVE_PATH,
    CodexInvocation,
    SummaryArtifact,
)

DEFAULT_CODEX_MODEL = "gpt-5.4"
DEFAULT_SUMMARY_FORMAT = "briefing-v1"
MAX_PROMPT_RAW_ITEMS = 200


class CodexCliSummarizer:
    def __init__(
        self,
        invocation: CodexInvocation | None = None,
        *,
        model: str = DEFAULT_CODEX_MODEL,
        summary_format: str = DEFAULT_SUMMARY_FORMAT,
    ) -> None:
        self._invocation = invocation or CodexCliInvocation(model=model)
        self._summary_format = summary_format

    def summarize_archive(self, archive_directory: str | Path) -> SummaryArtifact:
        archive_directory = Path(archive_directory)
        raw_items_path = archive_directory / RAW_ITEMS_RELATIVE_PATH
        raw_items = raw_items_path.read_text()
        prompt = build_codex_digest_prompt(archive_directory, raw_items, summary_format=self._summary_format)
        content = self._invocation.run(prompt, cwd=archive_directory)

        output_path = archive_directory / CODEX_DIGEST_RELATIVE_PATH
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)
        return SummaryArtifact(path=output_path, content=content)


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
) -> str:
    compact_raw_items, raw_item_counts = _compact_raw_items_for_prompt(raw_items)
    url_title_index = _build_url_title_index(raw_items, title_fetcher=title_fetcher)
    lines = [
        "あなたは Hermes Pulse の要約担当です。",
        "以下の archive directory から canonical digest を作成してください。",
        "出力は日本語の Markdown のみを返してください。前置きや説明は不要です。",
        "一次情報として raw/collected-items.json を最優先で根拠にしてください。",
        "補助的に既存の summary markdown があれば参照してよいですが、raw JSON と矛盾する場合は raw JSON を優先してください。",
        "本文中のリンクは可能な限り保持し、URL を壊さないでください。",
        "不明な点は断定せず、与えられた情報だけで簡潔に要約してください。",
        "raw/collected-items.json の全文は archive directory 内に残っている前提です。埋め込み JSON は要約用の抜粋なので、必要なら件数メタデータを踏まえて偏りに注意してください。",
        "",
        *build_summary_format_instructions(summary_format),
        "",
        f"archive_directory: {archive_directory}",
        "",
        "## raw item counts",
        "```json",
        json.dumps(raw_item_counts, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Primary grounding: raw/collected-items.json",
        "```json",
        compact_raw_items.rstrip(),
        "```",
        "",
        "## URL/title index for all URL-bearing items",
        "```json",
        url_title_index.rstrip(),
        "```",
    ]

    for relative_path, markdown in _existing_summary_markdown(archive_directory):
        lines.extend(
            [
                "",
                f"## Supplemental context: {relative_path.as_posix()}",
                "```markdown",
                markdown.rstrip(),
                "```",
            ]
        )

    lines.append("")
    return "\n".join(lines)


def build_summary_format_instructions(summary_format: str) -> list[str]:
    if summary_format == "briefing-v1":
        return [
            "出力フォーマットは briefing-v1 を厳守してください。",
            "見出しはこの順番で固定してください: `☀ *Hermes Pulse Morning Briefing*` / `▫ 主要トピック` / `▫ 今日の予定・期限`。",
            "リンクが必要な箇所は、該当する語句を Markdown リンク `[ラベル](URL)` として文中に埋め込んでください。",
            "URL を文末に列挙しないでください。裸の URL を単独で並べるのも避けてください。",
            "`▫ 主要トピック` は 3〜6 件の箇条書き、各項目は 1 行で要点→必要なら文中リンク。",
            "`▫ 主要トピック` は可能な限り source diversity を確保し、同一 source ばかりで埋めず、Apple/Anthropic/xAI/X/ChatGPT/Grok のうち実際に item がある source を優先的に分散して拾ってください。",
            "`▫ 今日の予定・期限` は当日または近い日時の予定だけを書く。無ければ `- 目立った予定なし`。",
        ]
    raise ValueError(f"Unsupported summary format: {summary_format}")


def _existing_summary_markdown(archive_directory: Path) -> list[tuple[Path, str]]:
    summary_directory = archive_directory / "summary"
    if not summary_directory.exists():
        return []

    markdown_files = []
    for path in sorted(summary_directory.glob("*.md")):
        if path.name == CODEX_DIGEST_RELATIVE_PATH.name:
            continue
        markdown_files.append((path.relative_to(archive_directory), path.read_text()))
    return markdown_files


def _compact_raw_items_for_prompt(raw_items: str) -> tuple[str, dict[str, int]]:
    items = json.loads(raw_items)
    compact_items: list[dict[str, object]] = []
    for item in items[:MAX_PROMPT_RAW_ITEMS]:
        timestamps = item.get("timestamps") or {}
        provenance = item.get("provenance") or {}
        compact_items.append(
            {
                "id": item.get("id"),
                "source": item.get("source"),
                "source_kind": item.get("source_kind"),
                "title": _truncate_text(item.get("title")),
                "excerpt": _truncate_text(item.get("excerpt"), max_length=280),
                "body": _truncate_text(item.get("body"), max_length=280),
                "url": item.get("url"),
                "timestamps": {
                    "created_at": timestamps.get("created_at"),
                    "updated_at": timestamps.get("updated_at"),
                    "start_at": timestamps.get("start_at"),
                    "end_at": timestamps.get("end_at"),
                },
                "provenance": {
                    "provider": provenance.get("provider"),
                    "acquisition_mode": provenance.get("acquisition_mode"),
                    "authority_tier": provenance.get("authority_tier"),
                    "primary_source_url": provenance.get("primary_source_url"),
                    "raw_record_id": provenance.get("raw_record_id"),
                },
            }
        )
    raw_item_counts = {
        "total_items": len(items),
        "included_in_prompt": len(compact_items),
        "omitted_from_prompt": max(len(items) - len(compact_items), 0),
    }
    return json.dumps(compact_items, ensure_ascii=False, indent=2) + "\n", raw_item_counts


def _truncate_text(value: object, *, max_length: int = 160) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 1]}…"


def _build_url_title_index(raw_items: str, *, title_fetcher=None) -> str:
    items = json.loads(raw_items)
    fetcher = title_fetcher or _fetch_title_from_url
    indexed_items: list[dict[str, object]] = []
    for item in items:
        url = item.get("url")
        if not isinstance(url, str) or not url:
            continue
        title = _truncate_text(item.get("title"))
        if title is None:
            title = _truncate_text(fetcher(url)) or _fallback_title_for_url_item(item, url)
        indexed_items.append(
            {
                "id": item.get("id"),
                "source": item.get("source"),
                "title": title,
                "url": url,
            }
        )
    return json.dumps(indexed_items, ensure_ascii=False, indent=2) + "\n"


def _fallback_title_for_url_item(item: dict[str, object], url: str) -> str:
    title = _truncate_text(item.get("excerpt")) or _truncate_text(item.get("body"))
    if title:
        return title
    source = item.get("source")
    item_id = item.get("id")
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    return " / ".join(str(part) for part in (source, item_id, f"{parsed.netloc}{path}") if part)


class _TitleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_title = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.parts.append(data)


def _fetch_title_from_url(url: str) -> str | None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "HermesPulse/1.0 (+https://github.com/2001Y/hermes-pulse)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            content_type = response.headers.get("Content-Type", "")
            if "html" not in content_type:
                return None
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read(65536).decode(charset, errors="replace")
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None

    parser = _TitleParser()
    parser.feed(body)
    title = " ".join("".join(parser.parts).split())
    return title or None
