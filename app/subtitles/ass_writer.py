from __future__ import annotations

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


def write_ass(
    document: TranscriptDocument,
    output_path: Path,
    font_size: float = 32,
    position_x_percent: float = 50,
    bottom_percent: float = 8,
) -> Path:
    safe_font_size = max(8, min(64, int(round(font_size))))
    safe_x = max(10.0, min(90.0, float(position_x_percent)))
    safe_bottom = max(3.0, min(45.0, float(bottom_percent)))
    position_x = round(PLAY_RES_X * safe_x / 100)
    position_y = round(PLAY_RES_Y * (1 - safe_bottom / 100))

    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {PLAY_RES_X}",
        f"PlayResY: {PLAY_RES_Y}",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Arial,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,"
        "-1,0,0,0,100,100,0,0,1,3,1,2,20,20,20,1".format(font_size=safe_font_size),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    for segment in document.segments:
        subtitle_text = escape_ass_text(segment.subtitle_text or segment.translated_text or segment.text)
        if not subtitle_text:
            continue
        lines.append(
            "Dialogue: 0,{start},{end},Default,,0,0,0,,{{\\pos({x},{y})}}{text}".format(
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
