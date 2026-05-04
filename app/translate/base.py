from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

from app.models import TranscriptSegment


class TranslatorBackend(ABC):
    @abstractmethod
    def translate_segments(
        self,
        segments: list[TranscriptSegment],
        source_language: str,
        target_language: str,
        progress_callback: Callable[[float], None] | None = None,
    ) -> list[str]:
        raise NotImplementedError
