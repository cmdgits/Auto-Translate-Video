from __future__ import annotations

import time
from typing import Callable

import httpx

from app.core.exceptions import ConfigurationError, ProcessError
from app.models import TranscriptSegment
from app.translate.base import TranslatorBackend
from app.translate.http_errors import format_translator_http_error
from app.translate.llm_prompt import SYSTEM_PROMPT, build_translation_user_prompt, parse_translation_json
from app.translate.retry import post_with_retry


DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"


def normalize_gemini_model(model: str | None) -> str:
    model_name = (model or DEFAULT_GEMINI_MODEL).strip()
    if not model_name:
        return DEFAULT_GEMINI_MODEL
    if "/models/" in model_name:
        model_name = model_name.rsplit("/models/", 1)[1]
    if model_name.startswith("models/"):
        model_name = model_name.removeprefix("models/")
    if ":" in model_name:
        model_name = model_name.split(":", 1)[0]
    return model_name.strip("/") or DEFAULT_GEMINI_MODEL


class GeminiTranslatorBackend(TranslatorBackend):
    def __init__(
        self,
        api_key: str | None,
        model: str | None,
        batch_size: int,
        base_url: str | None = None,
        glossary: dict[str, str] | None = None,
    ) -> None:
        if not api_key:
            raise ConfigurationError("Chua cau hinh gemini_api_key hoac GEMINI_API_KEY.")
        self.api_key = api_key
        self.model = normalize_gemini_model(model)
        self.batch_size = batch_size
        self.base_url = (base_url or DEFAULT_GEMINI_BASE_URL).rstrip("/")
        self.glossary = glossary or {}

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
                user_prompt = build_translation_user_prompt(batch, source_language, target_language, self.glossary)
                response = post_with_retry(
                    client,
                    f"{self.base_url}/models/{self.model}:generateContent",
                    headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                    json={
                        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                        "generationConfig": {
                            "temperature": 0.2,
                            "responseMimeType": "application/json",
                        },
                    },
                )
                if response.status_code >= 400:
                    raise ProcessError(format_translator_http_error("Gemini", response))
                data = response.json()
                try:
                    content = data["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError) as exc:
                    raise ProcessError("Khong doc duoc content tu Gemini translator.") from exc
                translated_map = parse_translation_json(content)
                for segment in batch:
                    outputs.append(translated_map.get(segment.id, segment.text))
                if progress_callback:
                    progress_callback(len(outputs) / total_segments)
                time.sleep(3.5)
        return outputs
