from __future__ import annotations

from collections.abc import Mapping


class SourceCollectionError(RuntimeError):
    """Raised by a connector after independent source failures are recorded."""

    def __init__(self, errors: Mapping[str, str]) -> None:
        self.errors = dict(errors)
        details = "; ".join(
            f"{source_id}: {message}" for source_id, message in sorted(self.errors.items())
        )
        super().__init__(f"Source collection failed ({len(self.errors)} source(s)): {details}")
