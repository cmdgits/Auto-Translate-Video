from __future__ import annotations

import textwrap
from pathlib import Path

from app.models import TranscriptDocument


PLAY_RES_X = 1280
PLAY_RES_Y = 720


def format_ass_timestamp(seconds: float) -> str:
    total_centiseconds = max(0, int(round(seconds * 100)))
    hours, remainder = divmod(total_centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    secs, centiseconds = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def escape_ass_text(value: str) -> str:
    return (
        value.replace("{", "｛")
        .replace("}", "｝")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", r"\N")
        .strip()
    )


def wrap_ass_text(value: str, font_size: int, box_width_ratio: float, play_res_x: int = PLAY_RES_X) -> str:
    text = value.strip()
    if not text:
        return ""

    safe_box_width = max(0.1, min(1.0, float(box_width_ratio)))
    safe_play_res_x = max(1, int(play_res_x or PLAY_RES_X))
    approx_chars_per_line = max(8, min(120, int((safe_play_res_x * safe_box_width) / max(font_size * 0.58, 1))))
    wrapped_lines: list[str] = []
    for manual_line in text.split("\n"):
        line = manual_line.strip()
        if not line:
            continue
        wrapped = textwrap.wrap(
            line,
            width=approx_chars_per_line,
            break_long_words=False,
            break_on_hyphens=False,
        )
        wrapped_lines.extend(wrapped or [line])
    return "\n".join(wrapped_lines)


def compact_text(value: str | None) -> str:
    return " ".join(str(value or "").split())


def auto_wrapped_text(value: str, max_chars_per_line: int, max_lines: int) -> str:
    wrapped = textwrap.wrap(
        value.strip(),
        width=max(8, int(max_chars_per_line)),
        break_long_words=False,
        break_on_hyphens=False,
    )
    if not wrapped:
        return value.strip()
    if len(wrapped) > max_lines:
        first_lines = wrapped[: max_lines - 1]
        last_line = " ".join(wrapped[max_lines - 1 :])
        wrapped = [*first_lines, last_line]
    return "\n".join(wrapped)


def render_text_for_segment(segment, auto_wrap_chars_per_line: int, auto_wrap_max_lines: int) -> str:
    subtitle_text = str(segment.subtitle_text or "").strip()
    translated_text = str(segment.translated_text or "").strip()
    source_text = str(segment.text or "").strip()
    if (
        subtitle_text
        and translated_text
        and compact_text(subtitle_text) == compact_text(translated_text)
        and subtitle_text == auto_wrapped_text(translated_text, auto_wrap_chars_per_line, auto_wrap_max_lines)
    ):
        return translated_text
    return subtitle_text or translated_text or source_text


def write_ass(
    document: TranscriptDocument,
    output_path: Path,
    font_size: float = 32,
    box_width_ratio: float = 0.84,
    position_x_percent: float = 50,
    bottom_percent: float = 8,
    auto_wrap_chars_per_line: int = 42,
    auto_wrap_max_lines: int = 2,
    play_res_x: int = PLAY_RES_X,
    play_res_y: int = PLAY_RES_Y,
) -> Path:
    safe_play_res_x = max(1, int(play_res_x or PLAY_RES_X))
    safe_play_res_y = max(1, int(play_res_y or PLAY_RES_Y))
    base_font_size = max(8, min(120, float(font_size)))
    safe_font_size = max(4, min(256, int(round(base_font_size * safe_play_res_y / PLAY_RES_Y))))
    safe_x = max(0.0, min(100.0, float(position_x_percent)))
    safe_bottom = max(0.0, min(100.0, float(bottom_percent)))
    position_x = round(safe_play_res_x * safe_x / 100)
    position_y = round(safe_play_res_y * (1 - safe_bottom / 100))

    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {safe_play_res_x}",
        f"PlayResY: {safe_play_res_y}",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Arial,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,"
        "-1,0,0,0,100,100,0,0,1,3,1,2,20,20,0,1".format(font_size=safe_font_size),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    for segment in document.segments:
        subtitle_text = escape_ass_text(
            wrap_ass_text(
                render_text_for_segment(segment, auto_wrap_chars_per_line, auto_wrap_max_lines),
                safe_font_size,
                box_width_ratio,
                safe_play_res_x,
            )
        )
        if not subtitle_text:
            continue
        lines.append(
            "Dialogue: 0,{start},{end},Default,,0,0,0,,{{\\an2\\pos({x},{y})}}{text}".format(
                start=format_ass_timestamp(segment.start),
                end=format_ass_timestamp(segment.end),
                x=position_x,
                y=position_y,
                text=subtitle_text,
            )
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return output_path
