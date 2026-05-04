from __future__ import annotations

from pathlib import Path

from app.media.ffmpeg import ensure_binary, run_process


def extract_audio_to_wav(
    input_path: Path,
    output_path: Path,
    ffmpeg_bin: str,
    sample_rate: int = 16000,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ensure_binary(ffmpeg_bin),
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]
    run_process(command)
    return output_path

