from __future__ import annotations

from typing import Callable

from app.models import TranscriptSegment
from app.translate.base import TranslatorBackend


class EchoTranslatorBackend(TranslatorBackend):
    def translate_segments(
        self,
        segments: list[TranscriptSegment],
        source_language: str,
        target_language: str,
        progress_callback: Callable[[float], None] | None = None,
    ) -> list[str]:
        if progress_callback:
            progress_callback(1.0)
        return [segment.text for segment in segments]
