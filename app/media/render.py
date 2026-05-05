from __future__ import annotations

from pathlib import Path
from typing import Callable

from app.config import RenderConfig
from app.media.ffmpeg import ensure_binary, run_ffmpeg_process
from app.media.ocr_blur import blur_text_in_video_with_ocr


def escape_subtitle_filter_path(path: Path) -> str:
    escaped = path.resolve().as_posix()
    escaped = escaped.replace("\\", "/")
    escaped = escaped.replace(":", r"\:")
    escaped = escaped.replace("'", r"\'")
    escaped = escaped.replace(",", r"\,")
    escaped = escaped.replace("[", r"\[")
    escaped = escaped.replace("]", r"\]")
    return escaped


def build_original_subtitle_cover_filter(render_config: RenderConfig) -> str:
    if not render_config.cover_original_subtitles:
        return ""
    cover_opacity = max(0.0, min(render_config.subtitle_cover_opacity, 1.0))
    if cover_opacity <= 0:
        return ""

    cover_height_ratio = max(0.03, min(render_config.subtitle_cover_height_ratio, 0.16))
    subtitle_x_ratio = max(0.12, min(float(render_config.subtitle_position_x) / 100, 0.88))
    subtitle_bottom_ratio = max(0.02, min(float(render_config.subtitle_position_y) / 100, 0.45))
    cover_width_ratio = max(0.28, min(float(render_config.subtitle_cover_width_ratio), 0.96))
    cover_left_ratio = max(0.0, min(subtitle_x_ratio - cover_width_ratio / 2, 1.0 - cover_width_ratio))
    cover_top = max(0.0, min(1.0 - subtitle_bottom_ratio - cover_height_ratio * 0.95, 1.0 - cover_height_ratio))
    cover_mode = str(render_config.subtitle_cover_mode or "blur").strip().lower()
    if cover_mode == "blur":
        return ""

    return (
        f"drawbox=x=iw*{cover_left_ratio:.3f}:y=ih*{cover_top:.3f}:"
        f"w=iw*{cover_width_ratio:.3f}:h=ih*{cover_height_ratio:.3f}:"
        f"color=black@{cover_opacity:.3f}:t=fill"
    )


def should_use_ocr_gaussian_blur(render_config: RenderConfig) -> bool:
    cover_mode = str(render_config.subtitle_cover_mode or "blur").strip().lower()
    return bool(
        render_config.cover_original_subtitles
        and cover_mode == "blur"
        and max(0.0, min(render_config.subtitle_cover_opacity, 1.0)) > 0
    )


def create_ocr_blurred_video(
    input_video: Path,
    output_video: Path,
    ffmpeg_bin: str,
    render_config: RenderConfig,
    progress_callback: Callable[[float], None] | None = None,
) -> Path:
    temporary_video = output_video.with_suffix(".ocr_blur.tmp.mp4")
    if temporary_video.exists():
        temporary_video.unlink()
    blur_text_in_video_with_ocr(
        input_video=input_video,
        output_video=temporary_video,
        ffmpeg_bin=ffmpeg_bin,
        render_config=render_config,
        video_encode_args=video_encode_args(render_config),
        progress_callback=progress_callback,
    )
    return temporary_video


def build_hardsub_filter(subtitle_path: Path, render_config: RenderConfig) -> str:
    subtitle_filter = f"subtitles='{escape_subtitle_filter_path(subtitle_path)}'"
    if subtitle_path.suffix.lower() != ".ass":
        subtitle_filter = f"{subtitle_filter}:charenc=UTF-8"
    cover_filter = build_original_subtitle_cover_filter(render_config)
    if not cover_filter:
        return subtitle_filter
    return f"{cover_filter},{subtitle_filter}"


def video_encode_args(render_config: RenderConfig) -> list[str]:
    codec = str(render_config.video_codec or "libx264").strip().lower()
    preset = str(render_config.preset or "medium").strip()
    quality = str(render_config.crf)
    args = ["-c:v", codec]
    if codec in {"libx264", "libx265"}:
        return [*args, "-preset", preset, "-crf", quality]
    if codec == "h264_nvenc":
        return [*args, "-preset", preset, "-rc", "vbr", "-cq", quality, "-b:v", "0"]
    if codec == "h264_qsv":
        return [*args, "-preset", preset, "-global_quality", quality]
    if codec == "h264_amf":
        return [*args, "-quality", preset, "-rc", "cqp", "-qp_i", quality, "-qp_p", quality, "-qp_b", quality]
    return [*args, "-preset", preset]


def burn_subtitles_into_video(
    input_video: Path,
    subtitle_path: Path,
    output_video: Path,
    ffmpeg_bin: str,
    render_config: RenderConfig,
    duration_sec: float | None = None,
    progress_callback: Callable[[float], None] | None = None,
) -> Path:
    output_video.parent.mkdir(parents=True, exist_ok=True)
    active_input_video = input_video
    if should_use_ocr_gaussian_blur(render_config):
        active_input_video = create_ocr_blurred_video(
            input_video=input_video,
            output_video=output_video,
            ffmpeg_bin=ffmpeg_bin,
            render_config=render_config,
            progress_callback=lambda value: progress_callback(value * 0.55) if progress_callback else None,
        )
    try:
        subtitle_filter = build_hardsub_filter(subtitle_path, render_config)
        filter_graph = f"[0:v]{subtitle_filter}[v]"
        command = [
            ensure_binary(ffmpeg_bin),
            "-y",
            "-i",
            str(active_input_video),
            "-filter_complex",
            filter_graph,
            "-map",
            "[v]",
            "-map",
            "0:a?",
            *video_encode_args(render_config),
            "-c:a",
            render_config.audio_codec,
            "-b:a",
            render_config.audio_bitrate,
            "-movflags",
            "+faststart",
            str(output_video),
        ]
        run_ffmpeg_process(
            command,
            duration_sec=duration_sec,
            progress_callback=(
                (lambda value: progress_callback(0.55 + value * 0.45))
                if progress_callback and active_input_video != input_video
                else progress_callback
            ),
        )
    finally:
        if active_input_video != input_video and active_input_video.exists():
            active_input_video.unlink()
    return output_video


def render_video_with_replaced_audio(
    input_video: Path,
    audio_path: Path,
    output_video: Path,
    ffmpeg_bin: str,
    render_config: RenderConfig,
    duration_sec: float | None = None,
    progress_callback: Callable[[float], None] | None = None,
) -> Path:
    output_video.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ensure_binary(ffmpeg_bin),
        "-y",
        "-i",
        str(input_video),
        "-i",
        str(audio_path),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "copy",
        "-shortest",
        "-movflags",
        "+faststart",
        str(output_video),
    ]
    run_ffmpeg_process(command, duration_sec=duration_sec, progress_callback=progress_callback)
    return output_video


def mux_subtitle_tracks_into_video(
    input_video: Path,
    subtitle_tracks: list[tuple[Path, str, str]],
    output_video: Path,
    ffmpeg_bin: str,
    render_config: RenderConfig,
    duration_sec: float | None = None,
    progress_callback: Callable[[float], None] | None = None,
    default_subtitle_index: int = 0,
) -> Path:
    if not subtitle_tracks:
        raise ValueError("Cần ít nhất một track phụ đề để mux softsub.")
    output_video.parent.mkdir(parents=True, exist_ok=True)
    active_input_video = input_video
    if should_use_ocr_gaussian_blur(render_config):
        active_input_video = create_ocr_blurred_video(
            input_video=input_video,
            output_video=output_video,
            ffmpeg_bin=ffmpeg_bin,
            render_config=render_config,
            progress_callback=lambda value: progress_callback(value * 0.82) if progress_callback else None,
        )
    subtitle_codec = "srt" if output_video.suffix.lower() == ".mkv" else "mov_text"
    try:
        command = [ensure_binary(ffmpeg_bin), "-y", "-i", str(active_input_video)]
        for subtitle_path, _, _ in subtitle_tracks:
            command.extend(["-i", str(subtitle_path)])
        cover_filter = build_original_subtitle_cover_filter(render_config)
        if cover_filter:
            command.extend(["-filter_complex", f"[0:v]{cover_filter}[v]"])
            command.extend(["-map", "[v]", "-map", "0:a?"])
        else:
            command.extend(["-map", "0:v:0", "-map", "0:a?"])
        for index in range(len(subtitle_tracks)):
            command.extend(["-map", f"{index + 1}:0"])
        if cover_filter:
            command.extend([
                *video_encode_args(render_config),
                "-c:a",
                "copy",
                "-c:s",
                subtitle_codec,
            ])
        else:
            command.extend(["-c:v", "copy", "-c:a", "copy", "-c:s", subtitle_codec])
        default_subtitle_index = max(0, min(default_subtitle_index, len(subtitle_tracks) - 1))
        for index, (_, language, title) in enumerate(subtitle_tracks):
            command.extend(["-metadata:s:s:" + str(index), f"language={language or 'und'}"])
            if title:
                command.extend(["-metadata:s:s:" + str(index), f"title={title}"])
            command.extend(["-disposition:s:" + str(index), "default+forced" if index == default_subtitle_index else "0"])
        if output_video.suffix.lower() != ".mkv":
            command.extend(["-movflags", "+faststart"])
        command.append(str(output_video))
        run_ffmpeg_process(
            command,
            duration_sec=duration_sec,
            progress_callback=(
                (lambda value: progress_callback(0.82 + value * 0.18))
                if progress_callback and active_input_video != input_video
                else progress_callback
            ),
        )
    finally:
        if active_input_video != input_video and active_input_video.exists():
            active_input_video.unlink()
    return output_video


def build_mux_subtitle_tracks_command_string(
    input_video: Path,
    subtitle_tracks: list[tuple[Path, str, str]],
    output_video: Path,
    ffmpeg_bin: str,
    render_config: RenderConfig,
    default_subtitle_index: int = 0,
) -> str:
    subtitle_codec = "srt" if output_video.suffix.lower() == ".mkv" else "mov_text"
    command = [ensure_binary(ffmpeg_bin), "-y", "-i", str(input_video)]
    for subtitle_path, _, _ in subtitle_tracks:
        command.extend(["-i", str(subtitle_path)])
    cover_filter = build_original_subtitle_cover_filter(render_config)
    if cover_filter:
        command.extend(["-filter_complex", f"[0:v]{cover_filter}[v]"])
        command.extend(["-map", "[v]", "-map", "0:a?"])
    else:
        command.extend(["-map", "0:v:0", "-map", "0:a?"])
    for index in range(len(subtitle_tracks)):
        command.extend(["-map", f"{index + 1}:0"])
    if cover_filter:
        command.extend([
            *video_encode_args(render_config),
            "-c:a",
            "copy",
            "-c:s",
            subtitle_codec,
        ])
    else:
        command.extend(["-c:v", "copy", "-c:a", "copy", "-c:s", subtitle_codec])
    default_subtitle_index = max(0, min(default_subtitle_index, len(subtitle_tracks) - 1))
    for index, (_, language, title) in enumerate(subtitle_tracks):
        command.extend(["-metadata:s:s:" + str(index), f"language={language or 'und'}"])
        if title:
            command.extend(["-metadata:s:s:" + str(index), f"title={title}"])
        command.extend(["-disposition:s:" + str(index), "default+forced" if index == default_subtitle_index else "0"])
    if output_video.suffix.lower() != ".mkv":
        command.extend(["-movflags", "+faststart"])
    command.append(str(output_video))
    return " ".join(f'"{item}"' if " " in item else item for item in command)
