from __future__ import annotations

from pathlib import Path
from typing import Callable

from app.config import RenderConfig
from app.core.exceptions import ProcessError
from app.media.ffmpeg import ensure_binary, ffmpeg_path, run_ffmpeg_process
from app.tts.edge_tts_backend import VoiceClip

BATCH_CLIP_LIMIT = 60


def ensure_voiceover_audio_output(output_audio: Path) -> Path:
    try:
        output_size = output_audio.stat().st_size
    except OSError as exc:
        raise ProcessError(f"FFmpeg khong tao duoc file audio thuyet minh: {output_audio}") from exc
    if output_size <= 0:
        output_audio.unlink(missing_ok=True)
        raise ProcessError(f"FFmpeg tao file audio thuyet minh 0 byte: {output_audio}")
    return output_audio


def _remove_file(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        raise ProcessError(f"Khong xoa duoc file audio cu: {path}") from exc


def _clip_batches(clips: list[VoiceClip], batch_size: int = BATCH_CLIP_LIMIT) -> list[list[VoiceClip]]:
    return [clips[index : index + batch_size] for index in range(0, len(clips), batch_size)]


def _write_tts_batch(
    clips: list[VoiceClip],
    output_audio: Path,
    filter_script_path: Path,
    ffmpeg_bin: str,
    render_config: RenderConfig,
    voiceover_gain: float,
    command_cwd: Path,
    duration_sec: float | None = None,
    progress_callback: Callable[[float], None] | None = None,
) -> Path:
    if not clips:
        raise ProcessError("Khong co segment nao de tao voice-over.")

    _remove_file(output_audio)
    output_audio.parent.mkdir(parents=True, exist_ok=True)
    filter_script_path.parent.mkdir(parents=True, exist_ok=True)

    command = [ensure_binary(ffmpeg_bin), "-y"]
    for clip in clips:
        command.extend(["-i", ffmpeg_path(clip.path, command_cwd)])

    safe_voiceover_gain = max(0.0, float(voiceover_gain))
    filter_lines: list[str] = []
    voice_inputs: list[str] = []
    for index, clip in enumerate(clips):
        delay_ms = max(0, int(round(clip.start * 1000)))
        label = f"tts{index}"
        filter_lines.append(
            f"[{index}:a]aresample=48000,adelay={delay_ms}:all=1,volume={safe_voiceover_gain:.3f}[{label}]"
        )
        voice_inputs.append(f"[{label}]")

    if len(voice_inputs) == 1:
        filter_lines.append(f"{voice_inputs[0]}anull[aout]")
    else:
        filter_lines.append(
            "".join(voice_inputs)
            + f"amix=inputs={len(voice_inputs)}:duration=longest:normalize=0:dropout_transition=0[aout]"
        )
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


def _mix_voice_batches_with_bed(
    input_video: Path,
    voice_batch_outputs: list[Path],
    output_audio: Path,
    filter_script_path: Path,
    ffmpeg_bin: str,
    render_config: RenderConfig,
    background_audio_gain: float,
    has_original_audio: bool,
    command_cwd: Path,
    duration_sec: float | None = None,
    progress_callback: Callable[[float], None] | None = None,
) -> Path:
    if not voice_batch_outputs:
        raise ProcessError("Khong tao duoc batch audio thuyet minh nao.")

    _remove_file(output_audio)
    command = [ensure_binary(ffmpeg_bin), "-y", "-i", ffmpeg_path(input_video, command_cwd)]
    for batch_output in voice_batch_outputs:
        command.extend(["-i", ffmpeg_path(batch_output, command_cwd)])

    filter_lines: list[str] = []
    voice_inputs = [f"[{index}:a]" for index in range(1, len(voice_batch_outputs) + 1)]
    if len(voice_inputs) == 1:
        filter_lines.append(f"{voice_inputs[0]}anull[voice_raw]")
    else:
        filter_lines.append(
            "".join(voice_inputs)
            + f"amix=inputs={len(voice_inputs)}:duration=longest:normalize=0:dropout_transition=0[voice_raw]"
        )

    safe_background_gain = max(0.0, float(background_audio_gain))
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
    command_cwd = filter_script_path.parent
    batches = _clip_batches(clips)
    voice_batch_outputs: list[Path] = []

    def emit(progress: float) -> None:
        if progress_callback:
            progress_callback(max(0.0, min(progress, 1.0)))

    try:
        for batch_index, batch in enumerate(batches):
            batch_output = command_cwd / f"voice_batch_{batch_index + 1:03d}.m4a"
            batch_filter = command_cwd / f"voice_batch_{batch_index + 1:03d}.ffscript"
            start_progress = batch_index / max(len(batches), 1) * 0.72
            end_progress = (batch_index + 1) / max(len(batches), 1) * 0.72
            voice_batch_outputs.append(
                _write_tts_batch(
                    batch,
                    batch_output,
                    batch_filter,
                    ffmpeg_bin,
                    render_config,
                    voiceover_gain,
                    command_cwd,
                    duration_sec=duration_sec,
                    progress_callback=(
                        lambda value, start=start_progress, end=end_progress: emit(start + value * (end - start))
                    ),
                )
            )

        return _mix_voice_batches_with_bed(
            input_video,
            voice_batch_outputs,
            output_audio,
            filter_script_path,
            ffmpeg_bin,
            render_config,
            background_audio_gain,
            has_original_audio,
            command_cwd,
            duration_sec=duration_sec,
            progress_callback=lambda value: emit(0.72 + value * 0.28),
        )
    finally:
        for batch_output in voice_batch_outputs:
            _remove_file(batch_output)
