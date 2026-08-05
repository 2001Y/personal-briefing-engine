"""Deterministic Japanese visual newspaper built from archived Pulse slots.

The module deliberately keeps collection and summarisation out of the visual
consumer.  It consumes immutable slot snapshots, writes an editable HTML
source, asks the locally installed Chrome for a PDF, rasterises that PDF for
Slack, and creates an animated cover GIF from the first raster page.
"""
from __future__ import annotations

import hashlib
import html
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw

REQUIRED_SLOTS = ("morning", "afternoon", "evening")
SLOT_TIMES = {"morning": "08:00", "afternoon": "14:00", "evening": "22:00"}
SLOT_LABELS = {"morning": "朝刊", "afternoon": "昼刊", "evening": "夜刊"}
SUMMARY_RELATIVE_PATH = Path("summary/codex-digest.md")
SOURCE_ERRORS_RELATIVE_PATH = Path("metadata/source-errors.json")
RUN_RELATIVE_PATH = Path("metadata/run.json")
MANIFEST_NAME = "manifest.json"
DEFAULT_TIMEZONE = "Asia/Tokyo"
DEFAULT_CHROME_PATH = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
logger = logging.getLogger(__name__)


class NewspaperInputError(RuntimeError):
    """Raised when the previous day's newspaper inputs are incomplete."""


@dataclass(frozen=True)
class SlotSnapshot:
    local_date: str
    slot: str
    directory: Path
    summary_path: Path
    summary: str
    manifest: dict[str, Any]
    source_errors: dict[str, Any]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path, *, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise NewspaperInputError(f"invalid JSON: {path}") from exc


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _slot_destination(slot_root: str | Path, local_date: str, slot: str) -> Path:
    root = Path(slot_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    destination = root / local_date / slot
    resolved_destination = destination.resolve(strict=False)
    try:
        resolved_destination.relative_to(root)
    except ValueError as exc:
        raise NewspaperInputError("slot destination escapes slot root") from exc
    if destination.exists() and destination.is_symlink():
        raise NewspaperInputError("slot destination is a symlink")
    return destination


def _copy_if_present(source: Path, destination: Path) -> None:
    if source.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def snapshot_pulse_slot(
    source_directory: str | Path,
    slot_root: str | Path,
    *,
    local_date: str,
    slot: str,
    timezone_name: str = DEFAULT_TIMEZONE,
) -> Path:
    """Copy the canonical Pulse output into an immutable date/slot directory."""
    if slot not in REQUIRED_SLOTS:
        raise ValueError(f"unsupported slot: {slot}")
    try:
        parsed_date = date.fromisoformat(local_date)
    except ValueError as exc:
        raise ValueError(f"local_date must be ISO date: {local_date!r}") from exc
    if parsed_date.isoformat() != local_date:
        raise ValueError(f"local_date must be ISO date: {local_date!r}")
    source_directory = Path(source_directory)
    destination = _slot_destination(slot_root, local_date, slot)
    summary_source = source_directory / SUMMARY_RELATIVE_PATH
    source_errors_source = source_directory / SOURCE_ERRORS_RELATIVE_PATH
    if not summary_source.exists():
        raise FileNotFoundError(f"canonical summary is missing: {summary_source}")
    if not source_errors_source.exists():
        raise FileNotFoundError(f"source errors artifact is missing: {source_errors_source}")
    source_errors = _read_json(source_errors_source, default=None)
    if not isinstance(source_errors, dict):
        raise NewspaperInputError(f"source errors artifact is invalid: {source_errors_source}")
    summary_sha256 = _sha256(summary_source)
    existing_manifest_path = destination / MANIFEST_NAME
    if existing_manifest_path.exists():
        existing_manifest = _read_json(existing_manifest_path, default={})
        if isinstance(existing_manifest, dict) and existing_manifest.get("completion_status") == "completed":
            if existing_manifest.get("summary_sha256") == summary_sha256:
                return destination
            raise NewspaperInputError(f"immutable completed snapshot already exists: {destination}")

    summary_destination = destination / SUMMARY_RELATIVE_PATH
    summary_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(summary_source, summary_destination)
    for relative_path in (SOURCE_ERRORS_RELATIVE_PATH, RUN_RELATIVE_PATH, Path("metadata/codex-attempts.json")):
        _copy_if_present(source_directory / relative_path, destination / relative_path)

    source_errors = _read_json(destination / SOURCE_ERRORS_RELATIVE_PATH, default=source_errors)
    if source_errors:
        logger.warning("Pulse newspaper source warnings preserved: %s", ", ".join(sorted(source_errors)))
    run_metadata = _read_json(destination / RUN_RELATIVE_PATH, default={})
    if not isinstance(run_metadata, dict):
        run_metadata = {}
    manifest = {
        "schema_version": 1,
        "local_date": local_date,
        "timezone": timezone_name,
        "slot": slot,
        "scheduled_time": SLOT_TIMES[slot],
        "run_id": run_metadata.get("run_id") or run_metadata.get("execution_id"),
        "completion_status": "completed",
        "canonical_summary": str(SUMMARY_RELATIVE_PATH),
        "summary_sha256": summary_sha256,
        "source_errors": source_errors,
        "generated_at": _utc_now(),
    }
    _atomic_write_text(
        destination / MANIFEST_NAME,
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    )
    return destination


def _load_slot_snapshot(slot_directory: Path, expected_date: str, expected_slot: str) -> SlotSnapshot:
    manifest_path = slot_directory / MANIFEST_NAME
    summary_path = slot_directory / SUMMARY_RELATIVE_PATH
    if not manifest_path.exists():
        raise NewspaperInputError(f"{expected_slot}: manifest is missing")
    manifest = _read_json(manifest_path, default={})
    if not isinstance(manifest, dict):
        raise NewspaperInputError(f"{expected_slot}: manifest is invalid")
    if manifest.get("local_date") != expected_date or manifest.get("slot") != expected_slot:
        raise NewspaperInputError(f"{expected_slot}: manifest identity mismatch")
    if manifest.get("completion_status") != "completed":
        raise NewspaperInputError(f"{expected_slot}: run is not completed")
    if not summary_path.exists() or not summary_path.read_text(encoding="utf-8").strip():
        raise NewspaperInputError(f"{expected_slot}: canonical summary is missing or empty")
    source_errors = manifest.get("source_errors")
    if not isinstance(source_errors, dict):
        raise NewspaperInputError(f"{expected_slot}: source errors metadata is invalid")
    if source_errors:
        logger.warning(
            "Pulse newspaper slot source warnings preserved slot=%s sources=%s",
            expected_slot,
            ", ".join(sorted(source_errors)),
        )
    if manifest.get("summary_sha256") != _sha256(summary_path):
        raise NewspaperInputError(f"{expected_slot}: summary hash mismatch")
    return SlotSnapshot(
        local_date=expected_date,
        slot=expected_slot,
        directory=slot_directory,
        summary_path=summary_path,
        summary=summary_path.read_text(encoding="utf-8"),
        manifest=manifest,
        source_errors=source_errors,
    )


def load_previous_day_slots(
    slot_root: str | Path,
    target_date: date,
) -> list[SlotSnapshot]:
    """Load exactly the three required slots for one local calendar date."""
    local_date = target_date.isoformat()
    root = Path(slot_root) / local_date
    snapshots: list[SlotSnapshot] = []
    for slot in REQUIRED_SLOTS:
        snapshots.append(_load_slot_snapshot(root / slot, local_date, slot))
    return snapshots


def _visible_lines(summary: str, *, limit: int) -> list[str]:
    lines: list[str] = []
    for raw_line in summary.splitlines():
        line = raw_line.strip()
        if not line or line in {"---", "***"}:
            continue
        if line.startswith("```") or line.startswith("#"):
            continue
        if line.lower().startswith(("generated at:", "retrieved at:", "window:")):
            continue
        line = re.sub(r"^[-*▫•]\s*", "", line)
        lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def _markdown_inline_to_html(text: str) -> str:
    parts: list[str] = []
    cursor = 0
    pattern = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
    for match in pattern.finditer(text):
        parts.append(html.escape(text[cursor : match.start()]))
        label = html.escape(match.group(1))
        url = html.escape(match.group(2), quote=True)
        parts.append(f'<a href="{url}">{label}</a>')
        cursor = match.end()
    parts.append(html.escape(text[cursor:]))
    return "".join(parts)


def _plain_inline(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\(https?://[^)]+\)", r"\1", text)
    text = re.sub(r"https?://\S+", "", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def _source_urls(snapshots: Sequence[SlotSnapshot], limit: int = 16) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for snapshot in snapshots:
        for url in re.findall(r"https?://[^)\s>]+", snapshot.summary):
            url = url.rstrip(".,;")
            if url not in seen:
                urls.append(url)
                seen.add(url)
            if len(urls) >= limit:
                return urls
    return urls


def build_newspaper_html(snapshots: Sequence[SlotSnapshot], target_date: date) -> str:
    """Build a two-page, Japanese, original magical-broadsheet HTML source."""
    by_slot = {snapshot.slot: snapshot for snapshot in snapshots}
    cards: list[str] = []
    for slot in REQUIRED_SLOTS:
        snapshot = by_slot[slot]
        items = _visible_lines(snapshot.summary, limit=6)
        body = "".join(f"<li>{_markdown_inline_to_html(item)}</li>" for item in items)
        cards.append(
            "<article class=\"edition-card\">"
            f"<div class=\"edition-label\">{SLOT_LABELS[slot]} · {SLOT_TIMES[slot]} JST</div>"
            f"<h2>{html.escape(_plain_inline(items[0] if items else SLOT_LABELS[slot]))}</h2>"
            f"<ul>{body}</ul>"
            "</article>"
        )

    full_columns: list[str] = []
    for slot in REQUIRED_SLOTS:
        snapshot = by_slot[slot]
        items = _visible_lines(snapshot.summary, limit=18)
        body = "".join(f"<li>{_markdown_inline_to_html(item)}</li>" for item in items)
        full_columns.append(
            "<section class=\"column\">"
            f"<h3>{SLOT_LABELS[slot]} · {SLOT_TIMES[slot]}</h3>"
            f"<ul>{body}</ul>"
            "</section>"
        )

    sources = "".join(
        f"<li><a href=\"{html.escape(url, quote=True)}\">{html.escape(url)}</a></li>"
        for url in _source_urls(snapshots)
    )
    if not sources:
        sources = "<li>本文に抽出可能な出典URLはありません。</li>"

    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>Hermes Pulse 魔法新聞 {target_date.isoformat()}</title>
<style>
@page {{ size: A4; margin: 10mm; }}
:root {{ color-scheme: light; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; background: #f7f3ea; color: #191817; }}
body {{ font-family: "Hiragino Mincho ProN", "Hiragino Mincho Pro", serif; }}
.page {{ width: 190mm; min-height: 277mm; padding: 5mm; page-break-after: always; position: relative; background: #fcfaf3; }}
.page:last-child {{ page-break-after: auto; }}
.masthead {{ border-top: 2px solid #181818; border-bottom: 1px solid #181818; padding: 4mm 0 3mm; text-align: center; }}
.masthead .kicker {{ font-family: "Hiragino Kaku Gothic ProN", sans-serif; font-size: 9pt; letter-spacing: .35em; color: #6b111b; }}
.masthead h1 {{ margin: 2mm 0 1mm; font-size: 31pt; letter-spacing: .12em; }}
.masthead .date {{ font-family: "Hiragino Kaku Gothic ProN", sans-serif; font-size: 8pt; letter-spacing: .15em; }}
.ornament {{ text-align: center; color: #6b111b; font-size: 15pt; margin: 3mm 0; }}
.editions {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 4mm; margin-top: 5mm; }}
.edition-card {{ border-top: 1.5px solid #191817; padding-top: 2mm; }}
.edition-label {{ font-family: "Hiragino Kaku Gothic ProN", sans-serif; color: #6b111b; font-size: 8pt; letter-spacing: .08em; }}
.edition-card h2 {{ font-size: 13pt; line-height: 1.35; margin: 2mm 0; }}
ul {{ margin: 0; padding-left: 1.1em; }}
li {{ font-size: 8.3pt; line-height: 1.55; margin-bottom: 1.4mm; }}
a {{ color: #183b5b; text-decoration: underline; }}
.hero {{ border: 1px solid #777; margin: 7mm 0 5mm; min-height: 40mm; padding: 4mm; background: linear-gradient(135deg, #eee9dd, #fbfaf6); position: relative; }}
.hero-inner {{ display: grid; grid-template-columns: 1fr 42mm; gap: 5mm; align-items: center; min-height: 32mm; }}
.hero-copy h2 {{ margin: 0 0 2mm; font-size: 19pt; line-height: 1.3; }}
.hero-copy p {{ margin: 0; font-size: 10pt; line-height: 1.6; }}
.magic-photo {{ height: 32mm; border: 1px solid #575757; position: relative; overflow: hidden; background: radial-gradient(circle at 69% 28%, #f7f1dd 0 7%, transparent 8%), linear-gradient(165deg, #1d2530 0 35%, #4a5057 36% 49%, #b4b0a4 50% 100%); box-shadow: inset 0 0 0 2px #e8e1d1, inset 0 0 0 4px #6b111b; }}
.magic-photo::before {{ content: ""; position: absolute; left: 8%; right: 8%; bottom: 0; height: 58%; background: #25282b; clip-path: polygon(0 100%, 0 72%, 18% 45%, 29% 64%, 48% 25%, 59% 60%, 76% 34%, 100% 72%, 100% 100%); opacity: .9; }}
.magic-photo::after {{ content: "✦"; position: absolute; top: 8%; right: 13%; color: #f6edcc; font-size: 11pt; }}
.hero::after {{ content: "✦  ✧  ✦"; position: absolute; right: 5mm; bottom: 2mm; color: #6b111b; letter-spacing: .3em; }}
.timeline {{ margin-top: 6mm; border-top: 1px solid #191817; border-bottom: 1px solid #191817; padding: 3mm 0; display: flex; justify-content: space-between; font-family: "Hiragino Kaku Gothic ProN", sans-serif; font-size: 8pt; }}
.page-title {{ font-size: 18pt; margin: 0 0 4mm; border-bottom: 1px solid #191817; padding-bottom: 2mm; }}
.columns {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 5mm; }}
.column {{ border-left: 1px solid #999; padding-left: 4mm; }}
.column:first-child {{ border-left: 0; padding-left: 0; }}
.column h3 {{ margin: 0 0 2mm; font-size: 12pt; color: #6b111b; }}
.sources {{ margin-top: 5mm; border-top: 1px solid #191817; padding-top: 3mm; }}
.sources h3 {{ font-size: 11pt; margin: 0 0 2mm; }}
.sources li {{ font-family: "Hiragino Kaku Gothic ProN", sans-serif; font-size: 6.6pt; line-height: 1.25; margin-bottom: .8mm; word-break: break-all; }}
.footer {{ position: absolute; bottom: 3mm; left: 5mm; right: 5mm; text-align: center; font-family: "Hiragino Kaku Gothic ProN", sans-serif; font-size: 6.5pt; color: #555; }}
</style>
</head>
<body>
<section class="page">
  <header class="masthead"><div class="kicker">THE DAILY PULSE · 前日三刊集約</div><h1>Hermes Pulse 魔法新聞</h1><div class="date">{target_date.strftime('%Y年%m月%d日')} · 朝刊特別版</div></header>
  <div class="ornament">✦　✧　✦</div>
  <div class="hero"><div class="hero-inner"><div class="hero-copy"><h2>{html.escape(_plain_inline(_visible_lines(by_slot['morning'].summary, limit=1)[0] if _visible_lines(by_slot['morning'].summary, limit=1) else '前日の世界で起きたこと'))}</h2><p>朝・昼・夜のPulseを一枚の紙面に束ね、変化の流れと重要な話題を日本語で読みやすく整理しました。</p></div><div class="magic-photo" aria-label="動く写真風の表紙装飾"></div></div></div>
  <div class="timeline"><span>朝刊 08:00</span><span>昼刊 14:00</span><span>夜刊 22:00</span><span>Asia/Tokyo</span></div>
  <div class="editions">{''.join(cards)}</div>
  <div class="footer">Hermes Pulse · generated from completed archived slots · page 1</div>
</section>
<section class="page">
  <header class="masthead"><div class="kicker">ARCHIVE OF THE THREE EDITIONS</div><h1 class="page-title">三刊から読む、昨日の動き</h1><div class="date">{target_date.isoformat()}</div></header>
  <div class="columns">{''.join(full_columns)}</div>
  <div class="sources"><h3>出典索引</h3><ul>{sources}</ul></div>
  <div class="footer">Hermes Pulse · Japanese visual digest · page 2</div>
</section>
</body>
</html>
"""


def render_pdf_and_pages(
    html_path: str | Path,
    output_directory: str | Path,
    *,
    chrome_path: str | Path = DEFAULT_CHROME_PATH,
    timeout_seconds: int = 120,
) -> tuple[Path, list[Path]]:
    """Render HTML through Chrome and rasterise the resulting PDF pages."""
    import fitz

    html_path = Path(html_path).resolve()
    output_directory = Path(output_directory).resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    pdf_path = output_directory / "newspaper.pdf"
    if pdf_path.exists():
        pdf_path.unlink()
    chrome = Path(chrome_path)
    if not chrome.exists():
        raise FileNotFoundError(f"Chrome binary is missing: {chrome}")
    with tempfile.TemporaryDirectory(prefix="hermes-pulse-chrome-") as profile:
        command = [
            str(chrome),
            "--headless=new",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            f"--user-data-dir={profile}",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}",
            html_path.as_uri(),
        ]
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                break
            if process.poll() is not None:
                break
            time.sleep(0.25)
        if process.poll() is None:
            process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        detail = (stderr or stdout or "Chrome did not produce a PDF").strip()
        raise RuntimeError(f"Chrome PDF rendering failed: {detail[-2000:]}")

    document = fitz.open(pdf_path)
    page_paths: list[Path] = []
    try:
        for index in range(len(document)):
            page = document[index]
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
            page_path = output_directory / f"page-{index + 1:02d}.png"
            pixmap.save(page_path)
            page_paths.append(page_path)
    finally:
        document.close()
    if not page_paths:
        raise RuntimeError("Chrome PDF rendered zero pages")
    return pdf_path, page_paths


def create_cover_gif(
    page_path: str | Path,
    output_path: str | Path,
    *,
    frame_count: int = 8,
    duration_ms: int = 260,
) -> Path:
    """Create a restrained moving-ink cover without changing newspaper text."""
    if frame_count < 2:
        raise ValueError("frame_count must be at least 2")
    source = Image.open(page_path).convert("RGB")
    frames: list[Image.Image] = []
    width, height = source.size
    for index in range(frame_count):
        frame = source.copy().convert("RGBA")
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        sweep_x = int((width + 160) * index / (frame_count - 1)) - 160
        draw.rectangle((sweep_x, 0, sweep_x + 80, height), fill=(255, 248, 214, 18))
        inset = 10 + (index % 3)
        draw.rectangle((inset, inset, width - inset, height - inset), outline=(107, 17, 27, 190), width=3)
        for star_index in range(5):
            x = int((star_index + 1) * width / 6 + ((index * 17 + star_index * 13) % 23) - 11)
            y = int((star_index + 2) * height / 8)
            radius = 3 + ((index + star_index) % 3)
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(107, 17, 27, 150))
        frames.append(Image.alpha_composite(frame, overlay).convert("P", palette=Image.Palette.ADAPTIVE))
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        disposal=2,
        optimize=True,
    )
    return output_path


def create_newspaper_artifacts(
    snapshots: Sequence[SlotSnapshot],
    target_date: date,
    output_root: str | Path,
    *,
    chrome_path: str | Path = DEFAULT_CHROME_PATH,
) -> dict[str, Any]:
    """Write HTML, PDF, ordered pages, cover GIF, and an artifact manifest."""
    output_directory = (Path(output_root) / target_date.isoformat()).resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    html_path = output_directory / "newspaper.html"
    html_path.write_text(build_newspaper_html(snapshots, target_date), encoding="utf-8")
    pdf_path, page_paths = render_pdf_and_pages(
        html_path,
        output_directory,
        chrome_path=chrome_path,
    )
    cover_gif_path = output_directory / "cover.gif"
    create_cover_gif(page_paths[0], cover_gif_path)
    manifest = {
        "schema_version": 1,
        "local_date": target_date.isoformat(),
        "timezone": DEFAULT_TIMEZONE,
        "inputs": [
            {
                "slot": snapshot.slot,
                "run_id": snapshot.manifest.get("run_id"),
                "summary_sha256": snapshot.manifest.get("summary_sha256"),
            }
            for snapshot in snapshots
        ],
        "artifacts": {
            "html": html_path.name,
            "pdf": pdf_path.name,
            "pages": [path.name for path in page_paths],
            "cover_gif": cover_gif_path.name,
        },
        "generated_at": _utc_now(),
        "delivery": {"status": "pending"},
    }
    manifest_path = output_directory / MANIFEST_NAME
    _atomic_write_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return {
        "directory": output_directory,
        "html": html_path,
        "pdf": pdf_path,
        "pages": page_paths,
        "cover_gif": cover_gif_path,
        "manifest": manifest_path,
    }


def post_newspaper_files(
    paths: Sequence[str | Path],
    *,
    channel: str,
    uploader: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    """Upload the complete ordered image set as one Slack root batch."""
    normalized = [Path(path) for path in paths]
    if not normalized:
        raise ValueError("newspaper file set is empty")
    if not channel or channel == "all" or not channel.startswith("D"):
        raise ValueError("newspaper delivery requires one Slack DM channel")
    allowed_suffixes = {".gif", ".png", ".jpg", ".jpeg", ".webp"}
    unsupported = [str(path) for path in normalized if path.suffix.lower() not in allowed_suffixes]
    if unsupported:
        raise ValueError("newspaper upload accepts image files only: " + ", ".join(unsupported))
    missing = [str(path) for path in normalized if not path.exists() or not path.is_file()]
    if missing:
        raise FileNotFoundError("newspaper files are missing: " + ", ".join(missing))
    titles = [path.stem.replace("-", " ") for path in normalized]
    result = uploader(
        normalized,
        channel,
        initial_comment=None,
        titles=titles,
        thread_ts=None,
    )
    if not isinstance(result, dict) or result.get("ok") is not True:
        raise RuntimeError(f"Slack newspaper upload failed: {result!r}")
    uploaded_files = result.get("files")
    if not isinstance(uploaded_files, list) or len(uploaded_files) != len(normalized):
        count = len(uploaded_files) if isinstance(uploaded_files, list) else 0
        raise RuntimeError(f"Slack newspaper upload incomplete: uploaded {count}/{len(normalized)}")
    return result
