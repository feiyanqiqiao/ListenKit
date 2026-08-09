from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .errors import ListenKitError, RuntimeHealthError
from .health import EXPECTED_FASTER_WHISPER, inspect_runtime, python_is_314
from .platform_paths import default_runtime_dir, platform_id, runtime_python_path


@dataclass(frozen=True)
class PythonCommand:
    executable: str
    prefix_arguments: tuple[str, ...] = ()


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _candidate_commands(
    *, platform: str | None = None, environment: Mapping[str, str] | None = None
) -> list[PythonCommand]:
    env = os.environ if environment is None else environment
    override = env.get("LISTENKIT_FASTER_WHISPER_BOOTSTRAP_PYTHON")
    if override:
        return [PythonCommand(override)]

    if platform_id(platform) == "windows":
        return [
            PythonCommand("py", ("-3.14",)),
            PythonCommand("python3.14"),
            PythonCommand("python"),
        ]
    return [
        PythonCommand("/opt/homebrew/bin/python3.14"),
        PythonCommand("/opt/homebrew/opt/python@3.14/bin/python3.14"),
        PythonCommand("/usr/local/bin/python3.14"),
        PythonCommand("python3.14"),
        PythonCommand("python3"),
    ]


def _resolve_command(command: PythonCommand) -> PythonCommand | None:
    value = command.executable
    if os.path.dirname(value):
        path = Path(value).expanduser()
        if not path.is_file():
            return None
        return PythonCommand(str(path), command.prefix_arguments)
    resolved = shutil.which(value)
    if not resolved:
        return None
    return PythonCommand(resolved, command.prefix_arguments)


def _command_is_python314(command: PythonCommand) -> bool:
    result = subprocess.run(
        [
            command.executable,
            *command.prefix_arguments,
            "-c",
            "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 14) else 1)",
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def find_bootstrap_python314(
    *, platform: str | None = None, environment: Mapping[str, str] | None = None
) -> PythonCommand:
    for candidate in _candidate_commands(platform=platform, environment=environment):
        resolved = _resolve_command(candidate)
        if resolved and _command_is_python314(resolved):
            return resolved
    raise ListenKitError(
        "Python 3.14 is required. Install it or set "
        "LISTENKIT_FASTER_WHISPER_BOOTSTRAP_PYTHON."
    )


def initialize_runtime(
    *,
    runtime_dir: Path | None = None,
    platform: str | None = None,
    environment: Mapping[str, str] | None = None,
    force_repair: bool = False,
) -> Path:
    env = dict(os.environ if environment is None else environment)
    target_dir = runtime_dir or default_runtime_dir(platform=platform, environment=env)
    if "/Library/Mobile Documents/" in str(target_dir).replace("\\", "/"):
        raise RuntimeHealthError(
            f"Refusing to create ListenKit's native runtime in an iCloud-backed path: {target_dir}"
        )
    executable = runtime_python_path(target_dir, platform=platform)

    if executable.is_file():
        if not python_is_314(executable):
            raise RuntimeHealthError(
                f"Existing ListenKit runtime does not use Python 3.14: {executable}"
            )
        if not force_repair:
            try:
                inspect_runtime(executable, environment=env)
                return executable
            except RuntimeHealthError:
                pass
    else:
        bootstrap = find_bootstrap_python314(platform=platform, environment=env)
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                bootstrap.executable,
                *bootstrap.prefix_arguments,
                "-m",
                "venv",
                str(target_dir),
            ],
            check=False,
        )
        if result.returncode != 0:
            raise ListenKitError(f"Failed to create ListenKit runtime at: {target_dir}")

    requirements = repository_root() / "requirements-faster-whisper.txt"
    for arguments, description in (
        (["-m", "pip", "install", "--upgrade", "pip"], "upgrade pip"),
        (["-m", "pip", "install", "-r", str(requirements)], "install requirements"),
    ):
        result = subprocess.run([str(executable), *arguments], check=False)
        if result.returncode != 0:
            raise ListenKitError(f"Failed to {description} in: {executable}")

    metadata = inspect_runtime(executable, environment=env)
    if metadata.faster_whisper_version != EXPECTED_FASTER_WHISPER:
        raise RuntimeHealthError(
            f"ListenKit requires faster-whisper {EXPECTED_FASTER_WHISPER}: {executable}"
        )
    return executable
