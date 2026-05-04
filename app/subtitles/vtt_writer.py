from __future__ import annotations

from pathlib import Path

from app.models import TranscriptDocument
from app.subtitles.srt_writer import format_srt_timestamp


def format_vtt_timestamp(seconds: float) -> str:
    return format_srt_timestamp(seconds).replace(",", ".")


def write_vtt(document: TranscriptDocument, output_path: Path) -> Path:
    lines = ["WEBVTT", ""]
    for segment in document.segments:
        subtitle_text = segment.subtitle_text or segment.translated_text or segment.text
        lines.extend(
            [
                f"{format_vtt_timestamp(segment.start)} --> {format_vtt_timestamp(segment.end)}",
                subtitle_text.strip(),
                "",
            ]
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return output_path

