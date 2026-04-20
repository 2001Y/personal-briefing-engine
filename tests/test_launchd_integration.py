import plistlib
import shlex
from pathlib import Path

from hermes_pulse.launchd import (
    DirectDeliveryWrapperSpec,
    GeneratedLaunchdArtifacts,
    LaunchdPlistSpec,
    generate_launchd_artifacts,
    render_direct_delivery_wrapper,
    render_launchd_plist,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_render_direct_delivery_wrapper_targets_module_with_channel_thread_and_archive_args() -> None:
    spec = DirectDeliveryWrapperSpec(
        python_executable=Path("/opt/homebrew/bin/python3"),
        repo_root=REPO_ROOT,
        channel="C123456",
        thread_ts="1712345.6789",
        archive_root=Path("/Users/akitani/Pulse Archive"),
        x_signals="bookmarks,likes,home_timeline_reverse_chronological",
    )

    wrapper = render_direct_delivery_wrapper(spec)

    assert wrapper.startswith("#!/bin/zsh\nset -euo pipefail\n")
    assert f"cd {shlex.quote(str(REPO_ROOT))}" in wrapper
    assert str(REPO_ROOT / "src") in wrapper

    exec_line = next(line for line in wrapper.splitlines() if line.startswith("exec "))
    assert shlex.split(exec_line.removeprefix("exec ")) == [
        "/opt/homebrew/bin/python3",
        "-m",
        "hermes_pulse.direct_delivery",
        "--channel",
        "C123456",
        "--thread-ts",
        "1712345.6789",
        "--archive-root",
        "/Users/akitani/Pulse Archive",
        "--x-signals",
        "bookmarks,likes,home_timeline_reverse_chronological",
    ]


def test_render_launchd_plist_serializes_label_schedule_and_program_arguments() -> None:
    plist = render_launchd_plist(
        LaunchdPlistSpec(
            label="ai.hermes.pulse.direct-delivery",
            program_arguments=["/Users/akitani/bin/run-hermes-pulse.sh"],
            hour=8,
            minute=15,
            working_directory=REPO_ROOT,
            standard_out_path=Path("/tmp/hermes-pulse.out.log"),
            standard_error_path=Path("/tmp/hermes-pulse.err.log"),
        )
    )

    payload = plistlib.loads(plist.encode())

    assert payload["Label"] == "ai.hermes.pulse.direct-delivery"
    assert payload["ProgramArguments"] == ["/Users/akitani/bin/run-hermes-pulse.sh"]
    assert payload["StartCalendarInterval"] == {"Hour": 8, "Minute": 15}
    assert payload["WorkingDirectory"] == str(REPO_ROOT)
    assert payload["StandardOutPath"] == "/tmp/hermes-pulse.out.log"
    assert payload["StandardErrorPath"] == "/tmp/hermes-pulse.err.log"
    assert payload["RunAtLoad"] is False


def test_generate_launchd_artifacts_writes_wrapper_and_plist_to_output_directory(tmp_path: Path) -> None:
    output_directory = tmp_path / "generated"

    artifacts = generate_launchd_artifacts(
        output_directory,
        wrapper_spec=DirectDeliveryWrapperSpec(
            python_executable=Path("/opt/homebrew/bin/python3"),
            repo_root=REPO_ROOT,
            channel="C123456",
            archive_root=Path("/Users/akitani/Pulse"),
            x_signals="bookmarks,likes",
        ),
        plist_spec=LaunchdPlistSpec(
            label="ai.hermes.pulse.direct-delivery",
            program_arguments=[],
            hour=9,
            minute=5,
        ),
    )

    assert artifacts == GeneratedLaunchdArtifacts(
        wrapper_path=output_directory / "run-hermes-pulse-direct-delivery.sh",
        plist_path=output_directory / "ai.hermes.pulse.direct-delivery.plist",
    )
    assert artifacts.wrapper_path.exists()
    assert artifacts.plist_path.exists()
    assert artifacts.wrapper_path.stat().st_mode & 0o111

    wrapper = artifacts.wrapper_path.read_text()
    exec_line = next(line for line in wrapper.splitlines() if line.startswith("exec "))
    assert shlex.split(exec_line.removeprefix("exec ")) == [
        "/opt/homebrew/bin/python3",
        "-m",
        "hermes_pulse.direct_delivery",
        "--channel",
        "C123456",
        "--archive-root",
        "/Users/akitani/Pulse",
        "--x-signals",
        "bookmarks,likes",
    ]

    plist_payload = plistlib.loads(artifacts.plist_path.read_bytes())
    assert plist_payload["ProgramArguments"] == [str(artifacts.wrapper_path)]
    assert plist_payload["StartCalendarInterval"] == {"Hour": 9, "Minute": 5}
