from __future__ import annotations

from typing import Callable

import httpx

from app.core.exceptions import ConfigurationError, ProcessError
from app.models import TranscriptSegment
from app.translate.base import TranslatorBackend


class LibreTranslateBackend(TranslatorBackend):
    def __init__(self, base_url: str | None, api_key: str | None = None) -> None:
        if not base_url:
            raise ConfigurationError("Chua cau hinh libretranslate_url.")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def translate_segments(
        self,
        segments: list[TranscriptSegment],
        source_language: str,
        target_language: str,
        progress_callback: Callable[[float], None] | None = None,
    ) -> list[str]:
        outputs: list[str] = []
        total_segments = max(len(segments), 1)
        with httpx.Client(timeout=60.0) as client:
            for segment in segments:
                payload = {
                    "q": segment.text,
                    "source": source_language if source_language != "auto" else "auto",
                    "target": target_language,
                    "format": "text",
                }
                if self.api_key:
                    payload["api_key"] = self.api_key
                response = client.post(f"{self.base_url}/translate", json=payload)
                if response.status_code >= 400:
                    raise ProcessError(f"LibreTranslate loi: {response.status_code} {response.text}")
                data = response.json()
                translated = data.get("translatedText")
                if not translated:
                    raise ProcessError("LibreTranslate khong tra ve translatedText hop le.")
                outputs.append(translated.strip())
                if progress_callback:
                    progress_callback(len(outputs) / total_segments)
        return outputs
