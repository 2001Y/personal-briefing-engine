import json
import subprocess
import tempfile
from pathlib import Path

from hermes_pulse.summarization.base import (
    CODEX_DIGEST_RELATIVE_PATH,
    RAW_ITEMS_RELATIVE_PATH,
    CodexInvocation,
    SummaryArtifact,
)

DEFAULT_CODEX_MODEL = "gpt-5.4"
DEFAULT_SUMMARY_FORMAT = "briefing-v1"


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
    def __init__(self, executable: str = "codex", *, model: str = DEFAULT_CODEX_MODEL) -> None:
        self._executable = executable
        self._model = model

    def run(self, prompt: str, *, cwd: Path) -> str:
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".md") as output_file:
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
            )
            if completed.returncode != 0:
                raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "codex exec failed")
            return Path(output_file.name).read_text()


def build_codex_digest_prompt(
    archive_directory: Path,
    raw_items: str,
    *,
    summary_format: str = DEFAULT_SUMMARY_FORMAT,
) -> str:
    compact_raw_items = _compact_raw_items_for_prompt(raw_items)
    lines = [
        "あなたは Hermes Pulse の要約担当です。",
        "以下の archive directory から canonical digest を作成してください。",
        "出力は日本語の Markdown のみを返してください。前置きや説明は不要です。",
        "一次情報として raw/collected-items.json を最優先で根拠にしてください。",
        "補助的に既存の summary markdown があれば参照してよいですが、raw JSON と矛盾する場合は raw JSON を優先してください。",
        "本文中のリンクは可能な限り保持し、URL を壊さないでください。",
        "不明な点は断定せず、与えられた情報だけで簡潔に要約してください。",
        "",
        *build_summary_format_instructions(summary_format),
        "",
        f"archive_directory: {archive_directory}",
        "",
        "## Primary grounding: raw/collected-items.json",
        "```json",
        compact_raw_items.rstrip(),
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
            "見出しはこの順番で固定してください: `# Hermes Pulse Morning Briefing` / `## 主要トピック` / `## 今日の予定・期限` / `## 気になるメモ`。",
            "`## 主要トピック` は 3〜6 件の箇条書き、各項目は 1 行で要点→必要ならリンク。",
            "`## 今日の予定・期限` は当日または近い日時の予定だけを書く。無ければ `- 目立った予定なし`。",
            "`## 気になるメモ` は 0〜3 件の短い箇条書きに限定し、推測は書かない。無ければ `- 特になし`。",
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


def _compact_raw_items_for_prompt(raw_items: str) -> str:
    items = json.loads(raw_items)
    compact_items: list[dict[str, object]] = []
    for item in items:
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
    return json.dumps(compact_items, ensure_ascii=False, indent=2) + "\n"


def _truncate_text(value: object, *, max_length: int = 160) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 1]}…"
