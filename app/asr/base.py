from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path

from app.models import TranscriptDocument


class ASRBackend(ABC):
    @abstractmethod
    def transcribe(
        self,
        audio_path: Path,
        job_id: str,
        video_path: Path,
        duration_sec: float,
        progress_hook: Callable[[float], None] | None = None,
    ) -> TranscriptDocument:
        raise NotImplementedError
