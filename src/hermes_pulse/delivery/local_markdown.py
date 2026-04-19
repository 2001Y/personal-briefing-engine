from pathlib import Path

from hermes_pulse.delivery.base import DeliveryAdapter


class LocalMarkdownDelivery(DeliveryAdapter):
    def deliver(self, content: str, destination: str | Path) -> Path:
        output_path = Path(destination)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)
        return output_path
