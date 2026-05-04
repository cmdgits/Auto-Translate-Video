from __future__ import annotations

from typing import Callable

import httpx

from app.core.exceptions import ConfigurationError, ProcessError
from app.models import TranscriptSegment
from app.translate.base import TranslatorBackend
from app.translate.http_errors import format_translator_http_error
from app.translate.llm_prompt import SYSTEM_PROMPT, build_translation_user_prompt, parse_translation_json
from app.translate.retry import post_with_retry


class LLMHTTPTranslatorBackend(TranslatorBackend):
    def __init__(self, base_url: str | None, api_key: str | None, model: str | None, batch_size: int) -> None:
        if not base_url or not model:
            raise ConfigurationError("Chua cau hinh llm_base_url hoac llm_model.")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.batch_size = batch_size

    def translate_segments(
        self,
        segments: list[TranscriptSegment],
        source_language: str,
        target_language: str,
        progress_callback: Callable[[float], None] | None = None,
    ) -> list[str]:
        outputs: list[str] = []
        total_segments = max(len(segments), 1)
        with httpx.Client(timeout=120.0) as client:
            for start in range(0, len(segments), self.batch_size):
                batch = segments[start : start + self.batch_size]
                user_prompt = build_translation_user_prompt(batch, source_language, target_language)
                response = post_with_retry(
                    client,
                    f"{self.base_url}/chat/completions",
                    headers={
                        **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}),
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "temperature": 0.2,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                )
                if response.status_code >= 400:
                    raise ProcessError(format_translator_http_error("GPT/LLM", response))
                data = response.json()
                try:
                    content = data["choices"][0]["message"]["content"]
                except (KeyError, IndexError) as exc:
                    raise ProcessError("Khong doc duoc content tu LLM translator.") from exc
                translated_map = parse_translation_json(content)
                for segment in batch:
                    outputs.append(translated_map.get(segment.id, segment.text))
                if progress_callback:
                    progress_callback(len(outputs) / total_segments)
        return outputs
