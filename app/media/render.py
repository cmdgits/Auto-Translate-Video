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


def build_original_subtitle_cover_filter(render_config: RenderConfig) -> str:
    if not render_config.cover_original_subtitles:
        return ""
    cover_opacity = max(0.0, min(render_config.subtitle_cover_opacity, 1.0))
    if cover_opacity <= 0:
        return ""

    cover_height_ratio = max(0.03, min(render_config.subtitle_cover_height_ratio, 0.16))
    subtitle_x_ratio = max(0.12, min(float(render_config.subtitle_position_x) / 100, 0.88))
    subtitle_bottom_ratio = max(0.02, min(float(render_config.subtitle_position_y) / 100, 0.45))
    font_ratio = max(0.025, min(float(render_config.subtitle_font_size) / 720, 0.12))
    cover_width_ratio = max(0.28, min(0.70, font_ratio * 8.6))
    cover_left_ratio = max(0.0, min(subtitle_x_ratio - cover_width_ratio / 2, 1.0 - cover_width_ratio))
    cover_top = max(0.0, min(1.0 - subtitle_bottom_ratio - cover_height_ratio * 0.95, 1.0 - cover_height_ratio))
    cover_mode = str(render_config.subtitle_cover_mode or "blur").strip().lower()
    if cover_mode == "blur":
        gaussian_sigma = max(6.0, min(32.0, 8.0 + cover_opacity * 26.0))
        feather_px = max(8, min(48, round(float(render_config.subtitle_font_size) * 0.6)))
        return (
            f"split[base][blur_src];"
            f"[blur_src]crop=w=iw*{cover_width_ratio:.3f}:h=ih*{cover_height_ratio:.3f}:"
            f"x=iw*{cover_left_ratio:.3f}:y=ih*{cover_top:.3f},"
            f"gblur=sigma={gaussian_sigma:.1f}:steps=2,format=rgba,"
            f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
            f"a='255*{cover_opacity:.3f}*clip(min(min(X,W-1-X),min(Y,H-1-Y))/{feather_px},0,1)'"
            f"[blurred_cover];"
            f"[base][blurred_cover]overlay=x=W*{cover_left_ratio:.3f}:y=H*{cover_top:.3f}:"
            f"format=yuv420:alpha=straight"
        )

    return (
        f"drawbox=x=iw*{cover_left_ratio:.3f}:y=ih*{cover_top:.3f}:"
        f"w=iw*{cover_width_ratio:.3f}:h=ih*{cover_height_ratio:.3f}:"
        f"color=black@{cover_opacity:.3f}:t=fill"
    )


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
        *video_encode_args(render_config),
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
    run_ffmpeg_process(command, duration_sec=duration_sec, progress_callback=progress_callback)
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
