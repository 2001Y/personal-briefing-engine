from pathlib import Path
from typing import Protocol


class DeliveryAdapter(Protocol):
    def deliver(self, content: str, destination: str | Path) -> Path:
        ...
