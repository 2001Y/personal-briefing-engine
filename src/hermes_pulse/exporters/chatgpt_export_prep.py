import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any


class ChatGPTExportPreparer:
    def find_latest_export(self, input_dir: str | Path) -> Path:
        candidates = [
            path
            for path in sorted(Path(input_dir).glob("*.zip"))
            if path.is_file() and _looks_like_chatgpt_export_zip(path)
        ]
        if not candidates:
            raise FileNotFoundError("No ChatGPT export zip found")
        return max(candidates, key=lambda path: (path.stat().st_mtime, path.name))

    def refresh_latest_export(self, input_dir: str | Path, output_dir: str | Path) -> dict[str, Any]:
        latest_export = self.find_latest_export(input_dir)
        destination = Path(output_dir)
        existing_count = _read_existing_conversation_count(destination)
        with tempfile.TemporaryDirectory(prefix="chatgpt-refresh-") as temp_dir:
            staged_output = Path(temp_dir) / "prepared"
            prepared = self.prepare(latest_export, staged_output)
            if prepared["conversation_count"] == 0 and existing_count > 0:
                manifest_path = destination / "manifest.json"
                existing_manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
                existing_manifest["latest_export_conversation_count"] = 0
                existing_manifest["latest_export_source_path"] = str(latest_export)
                existing_manifest["import_status"] = "skipped_empty_export"
                manifest_path.write_text(json.dumps(existing_manifest, ensure_ascii=False, indent=2))
                return {
                    **existing_manifest,
                    "conversation_count": existing_count,
                    "latest_export_conversation_count": 0,
                    "source_path": str(latest_export),
                }
            destination.mkdir(parents=True, exist_ok=True)
            shutil.rmtree(destination, ignore_errors=True)
            shutil.copytree(staged_output, destination)
            return prepared

    def prepare(self, input_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
        source = Path(input_path)
        destination = Path(output_dir)
        extracted_dir = destination / "extracted" / "conversations"
        extracted_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="chatgpt-export-") as temp_dir:
            staging = Path(temp_dir)
            self._materialize_source(source, staging)
            conversations_path = _find_first_file(staging, "conversations.json")
            if conversations_path is None:
                raise FileNotFoundError("conversations.json not found in ChatGPT export")
            user_path = _find_first_file(staging, "user.json")
            export_manifest_path = _find_first_file(staging, "export_manifest.json")

            shutil.copy2(conversations_path, extracted_dir / "conversations.json")
            if user_path is not None:
                shutil.copy2(user_path, extracted_dir / "user.json")
            if export_manifest_path is not None:
                shutil.copy2(export_manifest_path, extracted_dir / "export_manifest.json")

        conversations = json.loads((extracted_dir / "conversations.json").read_text())
        if not isinstance(conversations, list):
            raise ValueError("ChatGPT conversations export must be a list")
        account = _extract_account(extracted_dir / "user.json")
        manifest = {
            "provider": "chatgpt",
            "acquisition_mode": "official_export",
            "import_status": "prepared",
            "conversation_count": len(conversations),
            "account": account,
            "source_path": str(source),
        }
        (destination / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
        return manifest

    def _materialize_source(self, source: Path, staging: Path) -> None:
        if source.is_dir():
            shutil.copytree(source, staging, dirs_exist_ok=True)
            _extract_nested_zips(staging)
            return
        if source.is_file() and source.suffix.lower() == ".zip":
            _extract_zip(source, staging)
            _extract_nested_zips(staging)
            return
        raise ValueError("ChatGPT export input must be a directory or .zip file")


def _extract_zip(zip_path: Path, target_dir: Path) -> None:
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(target_dir)


def _extract_nested_zips(root: Path) -> None:
    pending = sorted(path for path in root.rglob("*.zip") if path.is_file())
    while pending:
        zip_path = pending.pop(0)
        relative = zip_path.relative_to(root)
        extract_dir = root / relative.with_suffix("")
        extract_dir.mkdir(parents=True, exist_ok=True)
        _extract_zip(zip_path, extract_dir)
        zip_path.unlink()
        pending = sorted(path for path in root.rglob("*.zip") if path.is_file())



def _find_first_file(root: Path, filename: str) -> Path | None:
    for path in sorted(root.rglob(filename)):
        if path.is_file():
            return path
    return None



def _looks_like_chatgpt_export_zip(path: Path) -> bool:
    name = path.name.lower()
    return "openai-export" in name or "chatgpt" in name or "conversations__" in name



def _read_existing_conversation_count(output_dir: Path) -> int:
    conversations_path = output_dir / "extracted" / "conversations" / "conversations.json"
    if not conversations_path.exists():
        return 0
    payload = json.loads(conversations_path.read_text())
    return len(payload) if isinstance(payload, list) else 0



def _extract_account(user_path: Path) -> str | None:
    if not user_path.exists():
        return None
    payload = json.loads(user_path.read_text())
    if not isinstance(payload, dict):
        return None
    email = payload.get("email")
    return email if isinstance(email, str) and email else None
