from __future__ import annotations

import plistlib
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


DEFAULT_LAUNCHD_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
DEFAULT_WRAPPER_FILENAME = "run-codex-pulse-direct-delivery.sh"


@dataclass(frozen=True)
class DirectDeliveryWrapperSpec:
    python_executable: Path
    repo_root: Path
    channel: str
    thread_ts: str | None = None
    archive_root: Path | None = None
    source_registry: Path | None = None
    feed_fixture: Path | None = None
    search_fixture: Path | None = None
    hermes_history: Path | None = None
    notes: Path | None = None
    working_directory: Path | None = None


@dataclass(frozen=True)
class LaunchdPlistSpec:
    label: str
    program_arguments: Sequence[str]
    hour: int
    minute: int
    working_directory: Path | None = None
    standard_out_path: Path | None = None
    standard_error_path: Path | None = None
    run_at_load: bool = False

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("launchd label must not be empty")
        if not 0 <= self.hour <= 23:
            raise ValueError("launchd hour must be between 0 and 23")
        if not 0 <= self.minute <= 59:
            raise ValueError("launchd minute must be between 0 and 59")


@dataclass(frozen=True)
class GeneratedLaunchdArtifacts:
    wrapper_path: Path
    plist_path: Path


def build_direct_delivery_program_arguments(spec: DirectDeliveryWrapperSpec) -> list[str]:
    args = [
        str(spec.python_executable),
        "-m",
        "hermes_pulse.direct_delivery",
        "--channel",
        spec.channel,
    ]
    if spec.thread_ts is not None:
        args.extend(["--thread-ts", spec.thread_ts])
    if spec.archive_root is not None:
        args.extend(["--archive-root", str(spec.archive_root)])
    if spec.source_registry is not None:
        args.extend(["--source-registry", str(spec.source_registry)])
    if spec.feed_fixture is not None:
        args.extend(["--feed-fixture", str(spec.feed_fixture)])
    if spec.search_fixture is not None:
        args.extend(["--search-fixture", str(spec.search_fixture)])
    if spec.hermes_history is not None:
        args.extend(["--hermes-history", str(spec.hermes_history)])
    if spec.notes is not None:
        args.extend(["--notes", str(spec.notes)])
    return args


def render_direct_delivery_wrapper(spec: DirectDeliveryWrapperSpec) -> str:
    repo_root = Path(spec.repo_root)
    working_directory = Path(spec.working_directory or repo_root)
    python_path_root = repo_root / "src"
    command = " ".join(shlex.quote(argument) for argument in build_direct_delivery_program_arguments(spec))
    return "\n".join(
        [
            "#!/bin/zsh",
            "set -euo pipefail",
            "",
            f"export PATH={DEFAULT_LAUNCHD_PATH}",
            f"export PYTHONPATH={shlex.quote(str(python_path_root))}\"${{PYTHONPATH:+:$PYTHONPATH}}\"",
            "",
            f"cd {shlex.quote(str(working_directory))}",
            f"exec {command}",
            "",
        ]
    )


def render_launchd_plist(spec: LaunchdPlistSpec) -> str:
    payload: dict[str, object] = {
        "Label": spec.label,
        "ProgramArguments": [str(argument) for argument in spec.program_arguments],
        "StartCalendarInterval": {"Hour": spec.hour, "Minute": spec.minute},
        "RunAtLoad": spec.run_at_load,
    }
    if spec.working_directory is not None:
        payload["WorkingDirectory"] = str(spec.working_directory)
    if spec.standard_out_path is not None:
        payload["StandardOutPath"] = str(spec.standard_out_path)
    if spec.standard_error_path is not None:
        payload["StandardErrorPath"] = str(spec.standard_error_path)
    return plistlib.dumps(payload, sort_keys=False).decode()


def generate_launchd_artifacts(
    output_directory: str | Path,
    *,
    wrapper_spec: DirectDeliveryWrapperSpec,
    plist_spec: LaunchdPlistSpec,
    wrapper_filename: str = DEFAULT_WRAPPER_FILENAME,
    plist_filename: str | None = None,
) -> GeneratedLaunchdArtifacts:
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    wrapper_path = output_directory / wrapper_filename
    wrapper_path.write_text(render_direct_delivery_wrapper(wrapper_spec))
    wrapper_path.chmod(0o755)

    plist_path = output_directory / (plist_filename or f"{plist_spec.label}.plist")
    program_arguments = [str(argument) for argument in plist_spec.program_arguments] or [str(wrapper_path)]
    plist_path.write_text(
        render_launchd_plist(
            LaunchdPlistSpec(
                label=plist_spec.label,
                program_arguments=program_arguments,
                hour=plist_spec.hour,
                minute=plist_spec.minute,
                working_directory=plist_spec.working_directory,
                standard_out_path=plist_spec.standard_out_path,
                standard_error_path=plist_spec.standard_error_path,
                run_at_load=plist_spec.run_at_load,
            )
        )
    )

    return GeneratedLaunchdArtifacts(wrapper_path=wrapper_path, plist_path=plist_path)
