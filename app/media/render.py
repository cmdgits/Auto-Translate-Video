from __future__ import annotations

from pathlib import Path
from typing import Callable

from app.config import RenderConfig
from app.media.ffmpeg import ensure_binary, run_ffmpeg_process


def escape_subtitle_filter_path(path: Path) -> str:
    escaped = path.resolve().as_posix()
    escaped = escaped.replace("\\", "/")
    escaped = escaped.replace(":", r"\:")
    escaped = escaped.replace("'", r"\'")
    escaped = escaped.replace(",", r"\,")
    escaped = escaped.replace("[", r"\[")
    escaped = escaped.replace("]", r"\]")
    return escaped


def build_hardsub_filter(subtitle_path: Path, render_config: RenderConfig) -> str:
    subtitle_filter = f"subtitles='{escape_subtitle_filter_path(subtitle_path)}'"
    if subtitle_path.suffix.lower() != ".ass":
        subtitle_filter = f"{subtitle_filter}:charenc=UTF-8"
    if not render_config.cover_original_subtitles:
        return subtitle_filter

    cover_height_ratio = max(0.05, min(render_config.subtitle_cover_height_ratio, 0.45))
    cover_opacity = max(0.0, min(render_config.subtitle_cover_opacity, 1.0))
    cover_top = 1.0 - cover_height_ratio
    cover_mode = str(render_config.subtitle_cover_mode or "blur").strip().lower()
    if cover_mode == "blur":
        blur_radius = max(2, min(24, round(cover_opacity * 18)))
        cover_width_ratio = 0.76
        cover_left_ratio = (1.0 - cover_width_ratio) / 2
        cover_filter = (
            f"split[base][blur_src];"
            f"[blur_src]crop=w=iw*{cover_width_ratio:.3f}:h=ih*{cover_height_ratio:.3f}:"
            f"x=iw*{cover_left_ratio:.3f}:y=ih*{cover_top:.3f},"
            f"boxblur={blur_radius}:1[blurred_cover];"
            f"[base][blurred_cover]overlay=x=(W-w)/2:y=H-h"
        )
        return f"{cover_filter},{subtitle_filter}"

    cover_filter = (
        f"drawbox=x=0:y=ih*{cover_top:.3f}:w=iw:h=ih*{cover_height_ratio:.3f}:"
        f"color=black@{cover_opacity:.3f}:t=fill"
    )
    return f"{cover_filter},{subtitle_filter}"


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
    subtitle_filter = build_hardsub_filter(subtitle_path, render_config)
    filter_graph = f"[0:v]{subtitle_filter}[v]"
    command = [
        ensure_binary(ffmpeg_bin),
        "-y",
        "-i",
        str(input_video),
        "-filter_complex",
        filter_graph,
        "-map",
        "[v]",
        "-map",
        "0:a?",
        "-c:v",
        render_config.video_codec,
        "-preset",
        render_config.preset,
        "-crf",
        str(render_config.crf),
        "-c:a",
        render_config.audio_codec,
        "-b:a",
        render_config.audio_bitrate,
        "-movflags",
        "+faststart",
        str(output_video),
    ]
    run_ffmpeg_process(command, duration_sec=duration_sec, progress_callback=progress_callback)
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
        render_config.video_codec,
        "-preset",
        render_config.preset,
        "-crf",
        str(render_config.crf),
        "-c:a",
        render_config.audio_codec,
        "-b:a",
        render_config.audio_bitrate,
        "-shortest",
        "-movflags",
        "+faststart",
        str(output_video),
    ]
    run_ffmpeg_process(command, duration_sec=duration_sec, progress_callback=progress_callback)
    return output_video
