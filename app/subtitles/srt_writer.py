from __future__ import annotations

from pathlib import Path

from app.models import TranscriptDocument, TranscriptSegment


def _subtitle_text(segment: TranscriptSegment, text_mode: str) -> str:
    if text_mode == "source":
        return segment.text
    if text_mode == "translated":
        return segment.subtitle_text or segment.translated_text or segment.text
    return segment.subtitle_text or segment.translated_text or segment.text


def format_srt_timestamp(seconds: float) -> str:
    total_milliseconds = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(total_milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def write_srt(document: TranscriptDocument, output_path: Path, text_mode: str = "subtitle") -> Path:
    lines: list[str] = []
    for segment in document.segments:
        subtitle_text = _subtitle_text(segment, text_mode)
        lines.extend(
            [
                str(segment.id),
                f"{format_srt_timestamp(segment.start)} --> {format_srt_timestamp(segment.end)}",
                subtitle_text.strip(),
                "",
            ]
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return output_path
