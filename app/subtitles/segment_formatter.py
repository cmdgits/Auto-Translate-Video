from __future__ import annotations

import textwrap

from app.config import SubtitleConfig
from app.models import TranscriptSegment


def format_segments_for_subtitles(
    segments: list[TranscriptSegment],
    config: SubtitleConfig,
    preserve_existing: bool = False,
) -> list[TranscriptSegment]:
    formatted: list[TranscriptSegment] = []
    for segment in segments:
        if preserve_existing and segment.subtitle_text and segment.subtitle_text.strip():
            formatted.append(segment.model_copy(update={"subtitle_text": segment.subtitle_text.strip()}))
            continue
        subtitle_source = (segment.translated_text or segment.text).strip()
        wrapped = textwrap.wrap(
            subtitle_source,
            width=config.max_chars_per_line,
            break_long_words=False,
            break_on_hyphens=False,
        )
        if not wrapped:
            wrapped = [subtitle_source]
        if len(wrapped) > config.max_lines:
            first_lines = wrapped[: config.max_lines - 1]
            last_line = " ".join(wrapped[config.max_lines - 1 :])
            wrapped = [*first_lines, last_line]
        formatted.append(segment.model_copy(update={"subtitle_text": "\n".join(wrapped)}))
    return formatted
