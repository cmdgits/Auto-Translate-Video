from __future__ import annotations

import asyncio
import logging
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.config import TTSConfig
from app.core.exceptions import DependencyError
from app.models import TranscriptSegment

logger = logging.getLogger(__name__)


@dataclass
class VoiceClip:
    segment_id: int
    start: float
    end: float
    path: Path
    text: str
    voice_name: str | None = None


def estimate_edge_tts_rate(text: str, start: float, end: float, floor: int, ceil: int) -> int:
    duration = max(end - start, 0.45)
    word_count = max(1, len(text.split()))
    estimated_duration = max(word_count / 2.65, 0.6)
    ratio = estimated_duration / duration
    rate = round((ratio - 1.0) * 75)
    return max(floor, min(ceil, rate))


def sanitize_tts_text(text: str) -> str:
    compact_text = " ".join(str(text or "").split())
    cleaned_text = "".join(character for character in compact_text if not unicodedata.category(character).startswith("C"))
    return " ".join(cleaned_text.split())


class EdgeTTSBackend:
    def __init__(self, config: TTSConfig, voice_name: str | None = None) -> None:
        self.config = config
        self.voice_name = voice_name or config.voice
        self.warnings: list[str] = []

    def synthesize_segments(
        self,
        segments: list[TranscriptSegment],
        output_dir: Path,
        progress_callback: Callable[[float], None] | None = None,
    ) -> list[VoiceClip]:
        try:
            import edge_tts  # noqa: F401
        except ImportError as exc:
            raise DependencyError("Chua cai edge-tts. Hay cai dependency truoc khi render voice-over.") from exc
        return asyncio.run(self._synthesize_segments(segments, output_dir, progress_callback))

    async def _synthesize_segments(
        self,
        segments: list[TranscriptSegment],
        output_dir: Path,
        progress_callback: Callable[[float], None] | None = None,
    ) -> list[VoiceClip]:
        import edge_tts

        output_dir.mkdir(parents=True, exist_ok=True)
        self.warnings = []
        clips: list[VoiceClip] = []
        total_segments = max(len(segments), 1)
        for index, segment in enumerate(segments, start=1):
            spoken_text = sanitize_tts_text(segment.subtitle_text or segment.translated_text or segment.text)
            if not spoken_text:
                if progress_callback:
                    progress_callback(index / total_segments)
                continue
            speaker_key = (segment.speaker or "").strip()
            mapped_voice_name = self.config.speaker_voice_map.get(speaker_key) if speaker_key else None
            segment_voice_name = (segment.voice_name or mapped_voice_name or self.voice_name).strip()
            clip_path = output_dir / f"segment_{segment.id:04d}.mp3"
            if clip_path.exists():
                clip_path.unlink()
            rate_value = estimate_edge_tts_rate(
                spoken_text,
                segment.start,
                segment.end,
                self.config.rate_floor,
                self.config.rate_ceil,
            )
            try:
                await self._save_clip(edge_tts, spoken_text, clip_path, rate_value, segment_voice_name)
            except Exception as exc:
                try:
                    await self._save_clip(edge_tts, spoken_text, clip_path, 0, segment_voice_name)
                except Exception as retry_exc:
                    if clip_path.exists():
                        clip_path.unlink()
                    message = f"Bỏ qua đoạn {segment.id}: Edge TTS không tạo được audio ({retry_exc})"
                    self.warnings.append(message)
                    logger.warning(message, exc_info=exc)
                    if progress_callback:
                        progress_callback(index / total_segments)
                    continue
            if not clip_path.exists() or clip_path.stat().st_size <= 0:
                if clip_path.exists():
                    clip_path.unlink()
                message = f"Bỏ qua đoạn {segment.id}: Edge TTS trả về file audio rỗng."
                self.warnings.append(message)
                logger.warning(message)
                if progress_callback:
                    progress_callback(index / total_segments)
                continue
            clips.append(
                VoiceClip(
                    segment_id=segment.id,
                    start=segment.start,
                    end=segment.end,
                    path=clip_path,
                    text=spoken_text,
                    voice_name=segment_voice_name,
                )
            )
            if progress_callback:
                progress_callback(index / total_segments)
        return clips

    async def _save_clip(self, edge_tts, spoken_text: str, clip_path: Path, rate_value: int, voice_name: str) -> None:
        communicate = edge_tts.Communicate(
            spoken_text,
            voice=voice_name,
            rate=f"{rate_value:+d}%",
        )
        await communicate.save(str(clip_path))
