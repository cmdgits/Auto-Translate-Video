from __future__ import annotations

import shutil
import os
import sys
from collections.abc import Callable
from pathlib import Path

from app.asr.base import ASRBackend
from app.config import ASRConfig
from app.core.exceptions import DependencyError
from app.models import TranscriptDocument, TranscriptSegment


class FasterWhisperBackend(ASRBackend):
    def __init__(self, config: ASRConfig, model_size: str | None = None) -> None:
        self.config = config
        self.model_size = model_size or config.model_size

    def _resolve_device(self) -> tuple[str, str]:
        if self.config.device != "auto":
            compute_type = self.config.compute_type
            if compute_type == "auto":
                compute_type = "float16" if self.config.device == "cuda" else "int8"
            return self.config.device, compute_type
        device = "cuda" if shutil.which("nvidia-smi") else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        return device, compute_type

    def transcribe(
        self,
        audio_path: Path,
        job_id: str,
        video_path: Path,
        duration_sec: float,
        progress_hook: Callable[[float], None] | None = None,
    ) -> TranscriptDocument:
        os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
        try:
            from faster_whisper import WhisperModel
        except (ImportError, OSError) as exc:
            raise DependencyError(
                "Không tải được faster-whisper/ctranslate2 để nhận dạng giọng nói. "
                f"Python hiện tại: {sys.executable}. "
                "Trên Windows hãy chạy app bằng tools\\Python312\\python.exe, không dùng Python 3.14 hệ thống."
            ) from exc

        device, compute_type = self._resolve_device()
        model = WhisperModel(
            self.model_size,
            device=device,
            compute_type=compute_type,
            cpu_threads=self.config.cpu_threads,
            num_workers=self.config.num_workers,
        )
        segments, info = model.transcribe(
            str(audio_path),
            beam_size=self.config.beam_size,
            vad_filter=self.config.vad_filter,
            word_timestamps=self.config.word_timestamps,
        )
        rows = []
        last_reported_progress = 0.0
        for index, segment in enumerate(segments, start=1):
            text = " ".join(segment.text.split())
            if not text:
                continue
            rows.append(
                TranscriptSegment(
                    id=index,
                    start=float(segment.start),
                    end=float(segment.end),
                    text=text,
                )
            )
            if progress_hook and duration_sec > 0:
                current_progress = min(float(segment.end) / duration_sec, 0.98)
                if current_progress - last_reported_progress >= 0.02:
                    progress_hook(current_progress)
                    last_reported_progress = current_progress
        return TranscriptDocument(
            job_id=job_id,
            video_path=str(video_path),
            detected_language=getattr(info, "language", "unknown") or "unknown",
            duration_sec=duration_sec or float(getattr(info, "duration", 0.0) or 0.0),
            segments=rows,
        )
