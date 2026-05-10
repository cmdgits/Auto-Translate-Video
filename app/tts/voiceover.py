from __future__ import annotations

from pathlib import Path
from typing import Callable

from app.config import RenderConfig
from app.core.exceptions import ProcessError
from app.media.ffmpeg import ensure_binary, ffmpeg_path, run_ffmpeg_process
from app.tts.edge_tts_backend import VoiceClip


def ensure_voiceover_audio_output(output_audio: Path) -> Path:
    try:
        output_size = output_audio.stat().st_size
    except OSError as exc:
        raise ProcessError(f"FFmpeg khong tao duoc file audio thuyet minh: {output_audio}") from exc
    if output_size <= 0:
        output_audio.unlink(missing_ok=True)
        raise ProcessError(f"FFmpeg tao file audio thuyet minh 0 byte: {output_audio}")
    return output_audio


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
    output_audio.unlink(missing_ok=True)

    command_cwd = filter_script_path.parent
    command = [ensure_binary(ffmpeg_bin), "-y", "-i", ffmpeg_path(input_video, command_cwd)]
    for clip in clips:
        command.extend(["-i", ffmpeg_path(clip.path, command_cwd)])

    filter_lines: list[str] = []
    voice_inputs: list[str] = []
    safe_background_gain = max(0.0, float(background_audio_gain))
    safe_voiceover_gain = max(0.0, float(voiceover_gain))

    for index, clip in enumerate(clips, start=1):
        delay_ms = max(0, int(round(clip.start * 1000)))
        label = f"tts{index}"
        filter_lines.append(
            f"[{index}:a]aresample=48000,adelay={delay_ms}:all=1,volume={safe_voiceover_gain:.3f}[{label}]"
        )
        voice_inputs.append(f"[{label}]")

    if not voice_inputs:
        raise ProcessError("Khong tao duoc mix input cho voice-over.")

    if len(voice_inputs) == 1:
        filter_lines.append(f"{voice_inputs[0]}anull[voice_raw]")
    else:
        filter_lines.append(
            "".join(voice_inputs)
            + f"amix=inputs={len(voice_inputs)}:duration=longest:normalize=0:dropout_transition=0[voice_raw]"
        )

    if has_original_audio and safe_background_gain > 0:
        filter_lines.append(f"[0:a]aresample=48000,volume={safe_background_gain:.3f}[bed_raw]")
        filter_lines.append("[voice_raw]asplit[voice_side][voice_mix]")
        filter_lines.append(
            "[bed_raw][voice_side]"
            "sidechaincompress=threshold=0.030:ratio=12:attack=20:release=360:"
            "knee=2.5:link=maximum:detection=rms[bed_ducked]"
        )
        filter_lines.append(
            "[bed_ducked][voice_mix]amix=inputs=2:duration=longest:normalize=0:dropout_transition=0[aout]"
        )
    elif duration_sec and duration_sec > 0:
        filter_lines.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{duration_sec:.3f},asetpts=N/SR/TB[bed]")
        filter_lines.append(
            "[bed][voice_raw]amix=inputs=2:duration=longest:normalize=0:dropout_transition=0[aout]"
        )
    else:
        filter_lines.append("[voice_raw]anull[aout]")
    filter_script_path.write_text(";\n".join(filter_lines) + "\n", encoding="utf-8")

    command.extend(
        [
            "-filter_complex_script",
            ffmpeg_path(filter_script_path, command_cwd),
            "-map",
            "[aout]",
            "-c:a",
            render_config.audio_codec,
            "-b:a",
            render_config.audio_bitrate,
            ffmpeg_path(output_audio, command_cwd),
        ]
    )
    run_ffmpeg_process(command, duration_sec=duration_sec, progress_callback=progress_callback, cwd=command_cwd)
    return ensure_voiceover_audio_output(output_audio)
