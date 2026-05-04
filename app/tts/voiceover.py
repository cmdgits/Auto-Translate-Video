from __future__ import annotations

from pathlib import Path
from typing import Callable

from app.config import RenderConfig
from app.core.exceptions import ProcessError
from app.media.ffmpeg import ensure_binary, run_ffmpeg_process
from app.tts.edge_tts_backend import VoiceClip


def mix_voiceover_audio(
    input_video: Path,
    clips: list[VoiceClip],
    output_audio: Path,
    filter_script_path: Path,
    ffmpeg_bin: str,
    render_config: RenderConfig,
    background_audio_gain: float,
    voiceover_gain: float,
    has_original_audio: bool,
    duration_sec: float | None = None,
    progress_callback: Callable[[float], None] | None = None,
) -> Path:
    if not clips:
        raise ProcessError("Khong co segment nao de tao voice-over.")

    output_audio.parent.mkdir(parents=True, exist_ok=True)
    filter_script_path.parent.mkdir(parents=True, exist_ok=True)

    command = [ensure_binary(ffmpeg_bin), "-y", "-i", str(input_video)]
    for clip in clips:
        command.extend(["-i", str(clip.path)])

    filter_lines: list[str] = []
    mix_inputs: list[str] = []

    if has_original_audio:
        filter_lines.append(f"[0:a]volume={background_audio_gain:.3f},aresample=48000[bed]")
        mix_inputs.append("[bed]")

    for index, clip in enumerate(clips, start=1):
        delay_ms = max(0, int(round(clip.start * 1000)))
        label = f"tts{index}"
        filter_lines.append(
            f"[{index}:a]aresample=48000,adelay={delay_ms}:all=1,volume={voiceover_gain:.3f}[{label}]"
        )
        mix_inputs.append(f"[{label}]")

    if not mix_inputs:
        raise ProcessError("Khong tao duoc mix input cho voice-over.")

    filter_lines.append(
        "".join(mix_inputs)
        + f"amix=inputs={len(mix_inputs)}:normalize=0:dropout_transition=0[aout]"
    )
    filter_script_path.write_text(";\n".join(filter_lines) + "\n", encoding="utf-8")

    command.extend(
        [
            "-filter_complex_script",
            str(filter_script_path),
            "-map",
            "[aout]",
            "-c:a",
            render_config.audio_codec,
            "-b:a",
            render_config.audio_bitrate,
            str(output_audio),
        ]
    )
    run_ffmpeg_process(command, duration_sec=duration_sec, progress_callback=progress_callback)
    return output_audio
