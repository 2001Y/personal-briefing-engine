from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import fitz
from PIL import Image
import pytest

from hermes_pulse.visual_newspaper import (
    REQUIRED_SLOTS,
    NewspaperInputError,
    build_newspaper_html,
    create_cover_gif,
    load_previous_day_slots,
    post_newspaper_files,
    render_pdf_and_pages,
    snapshot_pulse_slot,
)


def _source_run(tmp_path: Path, slot: str, local_date: str = "2026-08-03") -> Path:
    source = tmp_path / f"source-{slot}"
    (source / "summary").mkdir(parents=True)
    (source / "metadata").mkdir()
    (source / "summary" / "codex-digest.md").write_text(
        f"# Hermes Pulse {slot}\n\n"
        f"## 見出し {slot}\n\n"
        f"- 日本語ニュース {slot} [出典](https://example.com/{slot})\n",
        encoding="utf-8",
    )
    (source / "metadata" / "source-errors.json").write_text("{}\n", encoding="utf-8")
    (source / "metadata" / "run.json").write_text(
        json.dumps({"run_id": f"run-{slot}", "local_date": local_date}, ensure_ascii=False),
        encoding="utf-8",
    )
    return source


def test_snapshot_preserves_summary_and_manifest_identity(tmp_path: Path) -> None:
    source = _source_run(tmp_path, "morning")

    snapshot = snapshot_pulse_slot(
        source,
        tmp_path / "slots",
        local_date="2026-08-03",
        slot="morning",
    )

    assert snapshot == tmp_path / "slots" / "2026-08-03" / "morning"
    manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["local_date"] == "2026-08-03"
    assert manifest["slot"] == "morning"
    assert manifest["completion_status"] == "completed"
    assert manifest["run_id"] == "run-morning"
    assert (snapshot / "summary" / "codex-digest.md").exists()


def test_snapshot_is_immutable_after_completed_write(tmp_path: Path) -> None:
    source = _source_run(tmp_path, "morning")
    slot_root = tmp_path / "slots"
    snapshot = snapshot_pulse_slot(source, slot_root, local_date="2026-08-03", slot="morning")
    (source / "summary" / "codex-digest.md").write_text("changed\n", encoding="utf-8")

    with pytest.raises(NewspaperInputError, match="immutable"):
        snapshot_pulse_slot(source, slot_root, local_date="2026-08-03", slot="morning")

    assert (snapshot / "summary" / "codex-digest.md").read_text(encoding="utf-8") != "changed\n"


def test_previous_day_requires_all_three_completed_slots(tmp_path: Path) -> None:
    slot_root = tmp_path / "slots"
    for slot in REQUIRED_SLOTS[:2]:
        snapshot_pulse_slot(
            _source_run(tmp_path, slot),
            slot_root,
            local_date="2026-08-03",
            slot=slot,
        )

    with pytest.raises(NewspaperInputError, match="evening"):
        load_previous_day_slots(slot_root, date(2026, 8, 3))


def test_snapshot_rejects_missing_source_errors(tmp_path: Path) -> None:
    source = _source_run(tmp_path, "morning")
    (source / "metadata" / "source-errors.json").unlink()
    with pytest.raises(FileNotFoundError, match="source errors"):
        snapshot_pulse_slot(source, tmp_path / "slots", local_date="2026-08-03", slot="morning")


def test_snapshot_rejects_non_iso_date_path(tmp_path: Path) -> None:
    source = _source_run(tmp_path, "morning")
    with pytest.raises(ValueError, match="local_date"):
        snapshot_pulse_slot(source, tmp_path / "slots", local_date="../outside", slot="morning")


def test_previous_day_preserves_non_empty_source_errors_as_warnings(tmp_path: Path) -> None:
    for slot in REQUIRED_SLOTS[:2]:
        snapshot_pulse_slot(
            _source_run(tmp_path, slot),
            tmp_path / "slots",
            local_date="2026-08-03",
            slot=slot,
        )
    source = _source_run(tmp_path, "evening")
    (source / "metadata" / "source-errors.json").write_text(
        '{"x": "timeout"}\n', encoding="utf-8"
    )
    snapshot_pulse_slot(
        source,
        tmp_path / "slots",
        local_date="2026-08-03",
        slot="evening",
    )

    snapshots = load_previous_day_slots(tmp_path / "slots", date(2026, 8, 3))

    assert snapshots[-1].source_errors == {"x": "timeout"}
    assert snapshots[-1].manifest["completion_status"] == "completed"


def test_newspaper_html_is_japanese_and_keeps_source_links(tmp_path: Path) -> None:
    snapshots = []
    for slot in REQUIRED_SLOTS:
        snapshots.append(
            snapshot_pulse_slot(
                _source_run(tmp_path, slot),
                tmp_path / "slots",
                local_date="2026-08-03",
                slot=slot,
            )
        )
    inputs = load_previous_day_slots(tmp_path / "slots", date(2026, 8, 3))

    html = build_newspaper_html(inputs, date(2026, 8, 3))

    assert "Hermes Pulse 魔法新聞" in html
    assert "朝刊" in html
    assert "昼刊" in html
    assert "夜刊" in html
    assert "https://example.com/morning" in html
    assert "ハリー・ポッター" not in html


def test_cover_gif_is_animated(tmp_path: Path) -> None:
    page = tmp_path / "page-01.png"
    Image.new("RGB", (240, 320), "white").save(page)
    gif_path = tmp_path / "cover.gif"

    create_cover_gif(page, gif_path, frame_count=4)

    with Image.open(gif_path) as image:
        assert image.format == "GIF"
        assert image.n_frames == 4
        assert image.info.get("duration")


def test_render_rejects_stale_pdf_when_chrome_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    html = tmp_path / "source.html"
    html.write_text("<html><body>test</body></html>", encoding="utf-8")
    output = tmp_path / "output"
    output.mkdir()
    stale_pdf = output / "newspaper.pdf"
    stale_pdf.write_bytes(b"stale")
    chrome = tmp_path / "chrome"
    chrome.write_bytes(b"fake")

    class FailedProcess:
        def poll(self) -> int:
            return 1

        def communicate(self, timeout: float | None = None) -> tuple[str, str]:
            return "", "chrome failed"

        def terminate(self) -> None:
            return None

        def wait(self, timeout: float | None = None) -> int:
            return 1

    monkeypatch.setattr(
        "hermes_pulse.visual_newspaper.subprocess.Popen",
        lambda *args, **kwargs: FailedProcess(),
    )

    with pytest.raises(RuntimeError, match="Chrome PDF rendering failed"):
        render_pdf_and_pages(html, output, chrome_path=chrome, timeout_seconds=1)
    assert not stale_pdf.exists()


def test_post_newspaper_files_uses_one_root_batch_without_comment_or_thread(tmp_path: Path) -> None:
    cover = tmp_path / "cover.gif"
    body = tmp_path / "page-02.png"
    for path, color in ((cover, "black"), (body, "white")):
        Image.new("RGB", (10, 10), color).save(path, format="GIF" if path.suffix == ".gif" else "PNG")

    calls: list[dict] = []

    def fake_uploader(paths, channel, **kwargs):
        calls.append({"paths": paths, "channel": channel, **kwargs})
        return {"ok": True, "files": [{"id": "F1"}, {"id": "F2"}]}

    result = post_newspaper_files(
        [cover, body],
        channel="D0AT8A3RB9A",
        uploader=fake_uploader,
    )

    assert result["ok"] is True
    assert len(calls) == 1
    assert calls[0]["paths"] == [cover, body]
    assert calls[0]["initial_comment"] is None
    assert calls[0]["thread_ts"] is None


def test_post_newspaper_files_rejects_incomplete_slack_response(tmp_path: Path) -> None:
    cover = tmp_path / "cover.gif"
    body = tmp_path / "page-02.png"
    for path in (cover, body):
        Image.new("RGB", (10, 10), "white").save(path, format="GIF" if path.suffix == ".gif" else "PNG")

    with pytest.raises(RuntimeError, match="uploaded 1/2"):
        post_newspaper_files(
            [cover, body],
            channel="D0AT8A3RB9A",
            uploader=lambda *_args, **_kwargs: {"ok": True, "files": [{"id": "F1"}]},
        )


def test_post_newspaper_files_rejects_non_dm_or_non_image_targets(tmp_path: Path) -> None:
    pdf = tmp_path / "newspaper.pdf"
    pdf.write_bytes(b"not an image")
    with pytest.raises(ValueError):
        post_newspaper_files([pdf], channel="D0AT8A3RB9A", uploader=lambda *_args, **_kwargs: {"ok": True})
    with pytest.raises(ValueError):
        post_newspaper_files([pdf], channel="all", uploader=lambda *_args, **_kwargs: {"ok": True})


def test_pdf_pages_are_ordered_by_page_number(tmp_path: Path) -> None:
    pdf = fitz.open()
    for _ in range(2):
        page = pdf.new_page(width=595, height=842)
        page.insert_text((50, 80), "Hermes Pulse", fontsize=20)
    pdf_path = tmp_path / "newspaper.pdf"
    pdf.save(pdf_path)
    pdf.close()

    document = fitz.open(pdf_path)
    assert len(document) == 2
    assert "Hermes Pulse" in document[0].get_text()
    assert "Hermes Pulse" in document[1].get_text()
    document.close()
