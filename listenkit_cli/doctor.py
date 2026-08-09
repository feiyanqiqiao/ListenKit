from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Mapping

from .asr_device import probe_cuda_devices, select_asr_device
from .cuda_runtime import nvidia_driver_available
from .health import RuntimeHealthError, inspect_runtime
from .platform_paths import (
    default_runtime_dir,
    huggingface_hub_cache_dir,
    platform_id,
    runtime_python_path,
)
from .process import find_command


def doctor_lines(environment: Mapping[str, str] | None = None) -> list[str]:
    env = dict(os.environ if environment is None else environment)
    current_platform = platform_id()
    runtime_dir = default_runtime_dir(environment=env)
    runtime_python = runtime_python_path(runtime_dir)
    hub_cache = huggingface_hub_cache_dir(environment=env)
    model_snapshots = hub_cache / "models--Systran--faster-whisper-small" / "snapshots"
    model_ready = model_snapshots.is_dir() and any(
        path.is_file() for path in model_snapshots.glob("*/model.bin")
    )
    lines = [
        f"platform={current_platform}",
        f"os_version={platform.platform()}",
        f"runtime_dir={runtime_dir}",
        f"runtime_python={runtime_python}",
        f"yt_dlp_path={find_command('yt-dlp') or 'missing'}",
        f"ffmpeg_path={find_command('ffmpeg') or 'missing'}",
        f"nvidia_smi_path={find_command('nvidia-smi') or 'missing'}",
        f"powershell_version={env.get('LISTENKIT_POWERSHELL_VERSION', 'not-applicable')}",
        f"huggingface_hub_cache={hub_cache}",
        f"model_small_cache={'ready' if model_ready else 'missing'}",
    ]
    if current_platform == "macos":
        lines.extend(
            [
                "acceleration_backend=apple-accelerate",
                "acceleration_kind=optimized-cpu",
                "gpu_backend=unsupported-by-ctranslate2-macos-wheel",
            ]
        )
    elif current_platform in {"windows", "linux"}:
        lines.extend(
            [
                "acceleration_backend=cuda-or-optimized-cpu",
                f"nvidia_driver={'ready' if nvidia_driver_available(env) else 'missing'}",
            ]
        )
    try:
        metadata = inspect_runtime(runtime_python, environment=env)
        lines.extend(metadata.as_lines())
        lines.append("import_health=ok")
        probe = probe_cuda_devices(runtime_python, environment=env)
        lines.append(f"cuda_device_count={len(probe.devices)}")
        if probe.error:
            lines.append(f"cuda_probe_error={probe.error}")
            lines.append("cuda_runtime=unprepared")
        elif probe.devices:
            lines.append("cuda_runtime=ready")
        for library, available in probe.libraries:
            safe_name = library.replace(".", "_").replace("-", "_")
            lines.append(
                f"cuda_library_{safe_name}={'ready' if available else 'missing'}"
            )
        for device in probe.devices:
            prefix = f"cuda_device_{device.index}"
            lines.extend(
                [
                    f"{prefix}_name={device.name or 'unknown'}",
                    f"{prefix}_compute_capability={device.compute_capability if device.compute_capability is not None else 'unknown'}",
                    f"{prefix}_memory_total_mib={device.total_memory_mib if device.total_memory_mib is not None else 'unknown'}",
                    f"{prefix}_memory_free_mib={device.free_memory_mib if device.free_memory_mib is not None else 'unknown'}",
                    f"{prefix}_compute_types={','.join(sorted(device.supported_compute_types))}",
                ]
            )
        selection = select_asr_device(probe)
        lines.append(f"asr_auto_device={selection.device}")
        lines.append(f"asr_auto_compute_type={selection.compute_type}")
        lines.append(f"asr_auto_reason={selection.reason}")
    except RuntimeHealthError as exc:
        lines.append("import_health=failed")
        lines.append(f"runtime_error={exc}")
    return lines
