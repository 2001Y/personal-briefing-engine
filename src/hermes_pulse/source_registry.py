from pathlib import Path

import yaml

from hermes_pulse.models import SourceRegistryEntry


def load_source_registry(path: str | Path) -> list[SourceRegistryEntry]:
    payload = yaml.safe_load(Path(path).read_text()) or {}
    raw_entries = payload.get("sources", [])
    return [SourceRegistryEntry(**entry) for entry in raw_entries]
