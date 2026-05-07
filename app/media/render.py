from __future__ import annotations

from pathlib import Path
from typing import Callable

from app.config import RenderConfig
from app.media.ffmpeg import ensure_binary, run_ffmpeg_process, get_available_video_encoders

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

    cover_height_ratio = max(0.01, min(float(render_config.subtitle_cover_height_ratio), 1.0))
    cover_width_ratio = max(0.01, min(float(render_config.subtitle_cover_width_ratio), 1.0))
    cover_x_ratio = max(0.0, min(float(getattr(render_config, "subtitle_cover_position_x", 50)) / 100, 1.0))
    cover_y_ratio = max(0.0, min(float(getattr(render_config, "subtitle_cover_position_y", 8)) / 100, 1.0))
    cover_left_ratio = (1.0 - cover_width_ratio) * cover_x_ratio
    cover_top = (1.0 - cover_height_ratio) * (1.0 - cover_y_ratio)
    cover_mode = str(render_config.subtitle_cover_mode or "box").strip().lower()
    if cover_mode in {"none", "off", "disabled"}:
        return ""

    blur_radius = max(3, min(30, int(round(cover_opacity * 22))))
    blur_power = max(1, min(4, int(round(cover_opacity * 3))))
    return (
        f"split[base][blur_src];"
        f"[blur_src]crop=w=iw*{cover_width_ratio:.3f}:h=ih*{cover_height_ratio:.3f}:"
        f"x=iw*{cover_left_ratio:.3f}:y=ih*{cover_top:.3f},"
        f"boxblur=luma_radius={blur_radius}:luma_power={blur_power}:"
        f"chroma_radius={blur_radius}:chroma_power={blur_power}[blur_roi];"
        f"[base][blur_roi]overlay=x=W*{cover_left_ratio:.3f}:y=H*{cover_top:.3f}"
    )


def build_hardsub_filter(subtitle_path: Path, render_config: RenderConfig) -> str:
    subtitle_filter = f"subtitles='{escape_subtitle_filter_path(subtitle_path)}'"
    if subtitle_path.suffix.lower() != ".ass":
        subtitle_filter = f"{subtitle_filter}:charenc=UTF-8"
    cover_filter = build_original_subtitle_cover_filter(render_config)
    if not cover_filter:
        return subtitle_filter
    return f"{cover_filter},{subtitle_filter}"


def select_video_codec(render_config: RenderConfig, ffmpeg_bin: str) -> str:
    codec = str(render_config.video_codec or "auto").strip().lower()
    if codec != "auto":
        return codec

    available = get_available_video_encoders(ffmpeg_bin)
    if "h264_nvenc" in available:
        return "h264_nvenc"
    if "h264_qsv" in available:
        return "h264_qsv"
    if "h264_amf" in available:
        return "h264_amf"
    return "libx264"


def video_encode_args(render_config: RenderConfig, codec: str) -> list[str]:
    preset = str(render_config.preset or "medium").strip()
    quality = str(render_config.crf)
    args = ["-c:v", codec]
    if codec in {"libx264", "libx265"}:
        return [*args, "-preset", preset, "-crf", quality, "-pix_fmt", "yuv420p"]
    if codec == "h264_nvenc":
        return [*args, "-preset", preset, "-rc", "vbr", "-cq", quality, "-b:v", "0", "-pix_fmt", "yuv420p"]
    if codec == "h264_qsv":
        return [*args, "-preset", preset, "-global_quality", quality, "-pix_fmt", "yuv420p"]
    if codec == "h264_amf":
        return [
            *args,
            "-quality",
            preset,
            "-rc",
            "cqp",
            "-qp_i",
            quality,
            "-qp_p",
            quality,
            "-qp_b",
            quality,
            "-pix_fmt",
            "yuv420p",
        ]
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
    codec = select_video_codec(render_config, ffmpeg_bin)

    def _build_command(current_codec: str):
        return [
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
            *video_encode_args(render_config, current_codec),
            "-c:a",
            render_config.audio_codec,
            "-b:a",
            render_config.audio_bitrate,
            "-movflags",
            "+faststart",
            str(output_video),
        ]

    try:
        run_ffmpeg_process(_build_command(codec), duration_sec=duration_sec, progress_callback=progress_callback)
    except Exception as e:
        from app.core.exceptions import ProcessError
        if isinstance(e, ProcessError) and codec in {"h264_nvenc", "h264_qsv", "h264_amf"}:
            import logging
            logging.getLogger(__name__).warning(f"GPU rendering with {codec} failed, falling back to libx264 CPU rendering. Error: {e}")
            if output_video.exists():
                output_video.unlink(missing_ok=True)
            run_ffmpeg_process(_build_command("libx264"), duration_sec=duration_sec, progress_callback=progress_callback)
        else:
            raise e
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
    cover_filter = build_original_subtitle_cover_filter(render_config)
    codec = select_video_codec(render_config, ffmpeg_bin) if cover_filter else "copy"

    def _build_command(current_codec: str):
        command = [ensure_binary(ffmpeg_bin), "-y", "-i", str(input_video)]
        for subtitle_path, _, _ in subtitle_tracks:
            command.extend(["-i", str(subtitle_path)])
        
        if cover_filter:
            command.extend(["-filter_complex", f"[0:v]{cover_filter}[v]"])
            command.extend(["-map", "[v]", "-map", "0:a?"])
        else:
            command.extend(["-map", "0:v:0", "-map", "0:a?"])
        for index in range(len(subtitle_tracks)):
            command.extend(["-map", f"{index + 1}:0"])
        if cover_filter:
            command.extend([
                *video_encode_args(render_config, current_codec),
                "-c:a",
                "copy",
                "-c:s",
                subtitle_codec,
            ])
        else:
            command.extend(["-c:v", "copy", "-c:a", "copy", "-c:s", subtitle_codec])
        default_subtitle_index_safe = max(0, min(default_subtitle_index, len(subtitle_tracks) - 1))
        for index, (_, language, title) in enumerate(subtitle_tracks):
            command.extend(["-metadata:s:s:" + str(index), f"language={language or 'und'}"])
            if title:
                command.extend(["-metadata:s:s:" + str(index), f"title={title}"])
            command.extend(["-disposition:s:" + str(index), "default+forced" if index == default_subtitle_index_safe else "0"])
        if output_video.suffix.lower() != ".mkv":
            command.extend(["-movflags", "+faststart"])
        command.append(str(output_video))
        return command

    try:
        run_ffmpeg_process(_build_command(codec), duration_sec=duration_sec, progress_callback=progress_callback)
    except Exception as e:
        from app.core.exceptions import ProcessError
        if isinstance(e, ProcessError) and codec in {"h264_nvenc", "h264_qsv", "h264_amf"}:
            import logging
            logging.getLogger(__name__).warning(f"GPU rendering with {codec} failed, falling back to libx264 CPU rendering. Error: {e}")
            if output_video.exists():
                output_video.unlink(missing_ok=True)
            run_ffmpeg_process(_build_command("libx264"), duration_sec=duration_sec, progress_callback=progress_callback)
        else:
            raise e
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
    codec = select_video_codec(render_config, ffmpeg_bin) if cover_filter else "copy"

    if cover_filter:
        command.extend(["-filter_complex", f"[0:v]{cover_filter}[v]"])
        command.extend(["-map", "[v]", "-map", "0:a?"])
    else:
        command.extend(["-map", "0:v:0", "-map", "0:a?"])
    for index in range(len(subtitle_tracks)):
        command.extend(["-map", f"{index + 1}:0"])
    if cover_filter:
        command.extend([
            *video_encode_args(render_config, codec),
            "-c:a",
            "copy",
            "-c:s",
            subtitle_codec,
        ])
    else:
        command.extend(["-c:v", "copy", "-c:a", "copy", "-c:s", subtitle_codec])
    default_subtitle_index_safe = max(0, min(default_subtitle_index, len(subtitle_tracks) - 1))
    for index, (_, language, title) in enumerate(subtitle_tracks):
        command.extend(["-metadata:s:s:" + str(index), f"language={language or 'und'}"])
        if title:
            command.extend(["-metadata:s:s:" + str(index), f"title={title}"])
        command.extend(["-disposition:s:" + str(index), "default+forced" if index == default_subtitle_index_safe else "0"])
    if output_video.suffix.lower() != ".mkv":
        command.extend(["-movflags", "+faststart"])
    command.append(str(output_video))
    return " ".join(f'"{item}"' if " " in item else item for item in command)
