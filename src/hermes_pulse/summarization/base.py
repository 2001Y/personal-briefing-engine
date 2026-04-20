from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


RAW_ITEMS_RELATIVE_PATH = Path("raw") / "collected-items.json"
CODEX_DIGEST_RELATIVE_PATH = Path("summary") / "codex-digest.md"


@dataclass(frozen=True)
class SummaryArtifact:
    path: Path
    content: str


class CodexInvocation(Protocol):
    def run(self, prompt: str, *, cwd: Path) -> str:
        ...


class Summarizer(Protocol):
    def summarize_archive(self, archive_directory: str | Path) -> SummaryArtifact:
        ...
