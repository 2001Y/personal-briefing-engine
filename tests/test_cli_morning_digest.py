import tomllib
from pathlib import Path

import hermes_pulse.cli


ROOT = Path(__file__).resolve().parents[1]


def test_main_entrypoint_exists_and_exits_successfully() -> None:
    assert hermes_pulse.cli.main([]) == 0


def test_main_writes_morning_digest_markdown_to_output_path(tmp_path: Path) -> None:
    output_path = tmp_path / "deliveries" / "morning-digest.md"

    assert hermes_pulse.cli.main(["--output", str(output_path)]) == 0
    assert output_path.exists()
    assert output_path.read_text().startswith("# Morning Digest\n")



def test_pyproject_declares_console_entrypoint() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())

    assert pyproject["project"]["scripts"]["hermes-pulse"] == "hermes_pulse.cli:main"
