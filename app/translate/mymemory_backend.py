"""MyMemory Translation API backend – miễn phí, không cần API key."""
from __future__ import annotations

import time
from typing import Callable

import httpx

from app.core.exceptions import ProcessError
from app.models import TranscriptSegment
from app.translate.base import TranslatorBackend


class MyMemoryTranslatorBackend(TranslatorBackend):
    """Dịch bằng MyMemory API (mymemory.translated.net).

    Miễn phí, không cần API key. Giới hạn ~5000 ký tự/request
    và khoảng 100 request/ngày cho IP ẩn danh.
    Nếu cung cấp email thì được 10.000 request/ngày.
    """

    BASE_URL = "https://api.mymemory.translated.net/get"

    def __init__(self, email: str | None = None) -> None:
        self.email = email

    def translate_segments(
        self,
        segments: list[TranscriptSegment],
        source_language: str,
        target_language: str,
        progress_callback: Callable[[float], None] | None = None,
    ) -> list[str]:
        src = source_language if source_language != "auto" else "en"
        lang_pair = f"{src}|{target_language}"
        total_segments = max(len(segments), 1)

        outputs: list[str] = []
        with httpx.Client(timeout=30.0) as client:
            for i, segment in enumerate(segments):
                params: dict[str, str] = {
                    "q": segment.text,
                    "langpair": lang_pair,
                }
                if self.email:
                    params["de"] = self.email

                response = client.get(self.BASE_URL, params=params)
                if response.status_code >= 400:
                    raise ProcessError(
                        f"MyMemory lỗi: {response.status_code} {response.text}"
                    )

                data = response.json()
                resp_data = data.get("responseData", {})
                translated = resp_data.get("translatedText", "")

                if not translated:
                    raise ProcessError(
                        "MyMemory không trả về bản dịch hợp lệ."
                    )

                outputs.append(translated.strip())
                if progress_callback:
                    progress_callback(len(outputs) / total_segments)

                if i < len(segments) - 1:
                    time.sleep(0.5)

        return outputs
