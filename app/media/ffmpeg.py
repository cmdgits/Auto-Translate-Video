from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Callable

from app.core.exceptions import DependencyError, ProcessError


def ensure_binary(binary_name: str) -> str:
    candidate = Path(binary_name)
    if candidate.exists():
        return str(candidate.resolve())
    resolved = shutil.which(binary_name)
    if resolved:
        return resolved
    raise DependencyError(
        f"Khong tim thay '{binary_name}' trong PATH. Cai FFmpeg roi them vao PATH truoc khi chay pipeline."
    )


def run_process(command: list[str], cwd: Path | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise ProcessError(completed.stderr.strip() or f"Lenh that bai: {' '.join(command)}")
    return completed.stdout.strip()


def _parse_ffmpeg_progress_seconds(line: str) -> float | None:
    key, _, raw_value = line.strip().partition("=")
    if not raw_value:
        return None
    if key in {"out_time_ms", "out_time_us"}:
        try:
            return max(0.0, int(raw_value) / 1_000_000)
        except ValueError:
            return None
    if key == "out_time":
        parts = raw_value.split(":")
        if len(parts) != 3:
            return None
        try:
            hours = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2])
        except ValueError:
            return None
        return max(0.0, hours * 3600 + minutes * 60 + seconds)
    return None


def run_ffmpeg_process(
    command: list[str],
    duration_sec: float | None = None,
    progress_callback: Callable[[float], None] | None = None,
    cwd: Path | None = None,
) -> str:
    if not progress_callback or not duration_sec or duration_sec <= 0:
        return run_process(command, cwd=cwd)

    ffmpeg_command = [command[0], "-nostats", "-progress", "pipe:1", *command[1:]]
    process = subprocess.Popen(
        ffmpeg_command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    output_lines: list[str] = []
    last_progress = -1.0
    if process.stdout:
        for line in process.stdout:
            output_lines.append(line)
            seconds = _parse_ffmpeg_progress_seconds(line)
            if seconds is not None:
                progress = max(0.0, min(seconds / duration_sec, 0.999))
                if progress - last_progress >= 0.005:
                    progress_callback(progress)
                    last_progress = progress
            elif line.strip() == "progress=end":
                progress_callback(1.0)
                last_progress = 1.0

    return_code = process.wait()
    if return_code != 0:
        error_tail = "".join(output_lines[-120:]).strip()
        raise ProcessError(error_tail or f"Lenh that bai: {' '.join(command)}")
    progress_callback(1.0)
    return "".join(output_lines).strip()


_AVAILABLE_ENCODERS_CACHE: set[str] | None = None


def get_available_video_encoders(ffmpeg_bin: str) -> set[str]:
    global _AVAILABLE_ENCODERS_CACHE
    if _AVAILABLE_ENCODERS_CACHE is not None:
        return _AVAILABLE_ENCODERS_CACHE

    try:
        binary = ensure_binary(ffmpeg_bin)
        output = run_process([binary, "-encoders"])
        encoders = set()
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("V") and len(line) > 6:
                parts = line[6:].split()
                if parts:
                    encoders.add(parts[0])
        _AVAILABLE_ENCODERS_CACHE = encoders
        return encoders
    except Exception:
        _AVAILABLE_ENCODERS_CACHE = set()
        return _AVAILABLE_ENCODERS_CACHE
