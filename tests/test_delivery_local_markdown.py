from pathlib import Path

from hermes_pulse.delivery.local_markdown import LocalMarkdownDelivery


def test_local_markdown_delivery_writes_markdown_file(tmp_path: Path) -> None:
    output_path = tmp_path / "deliveries" / "digest.md"
    markdown = "# Morning Digest\n\n## Today\n- None.\n"

    delivery = LocalMarkdownDelivery()
    written_path = delivery.deliver(markdown, output_path)

    assert written_path == output_path
    assert output_path.read_text() == markdown
