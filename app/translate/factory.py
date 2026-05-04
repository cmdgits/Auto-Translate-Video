from __future__ import annotations

from app.config import TranslationConfig
from app.core.exceptions import ConfigurationError
from app.models import PipelineRunOptions
from app.translate.base import TranslatorBackend
from app.translate.echo_backend import EchoTranslatorBackend
from app.translate.gemini_backend import DEFAULT_GEMINI_MODEL, GeminiTranslatorBackend
from app.translate.glossary import load_glossary
from app.translate.libretranslate_backend import LibreTranslateBackend
from app.translate.llm_http_backend import LLMHTTPTranslatorBackend
from app.translate.mymemory_backend import MyMemoryTranslatorBackend

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"


def build_translator(config: TranslationConfig, options: PipelineRunOptions) -> TranslatorBackend:
    backend_name = (options.translator_backend or config.backend).lower()
    glossary = load_glossary(options.glossary_text, options.glossary_json_path)
    if backend_name == "echo":
        return EchoTranslatorBackend()
    if backend_name == "mymemory":
        return MyMemoryTranslatorBackend(glossary=glossary)
    if backend_name == "libretranslate":
        return LibreTranslateBackend(
            base_url=options.libretranslate_url or config.libretranslate_url,
            api_key=options.libretranslate_api_key or config.libretranslate_api_key,
            glossary=glossary,
        )
    if backend_name in {"gpt", "openai"}:
        return LLMHTTPTranslatorBackend(
            base_url=options.openai_base_url or config.openai_base_url or DEFAULT_OPENAI_BASE_URL,
            api_key=options.openai_api_key or config.openai_api_key,
            model=options.openai_model or config.openai_model or "gpt-4o-mini",
            batch_size=config.batch_size,
            glossary=glossary,
        )
    if backend_name == "gemini":
        return GeminiTranslatorBackend(
            base_url=options.gemini_base_url or config.gemini_base_url,
            api_key=options.gemini_api_key or config.gemini_api_key,
            model=options.gemini_model or config.gemini_model or DEFAULT_GEMINI_MODEL,
            batch_size=config.batch_size,
            glossary=glossary,
        )
    if backend_name in {"llm-http", "openai-compatible", "llm"}:
        return LLMHTTPTranslatorBackend(
            base_url=options.llm_base_url or config.llm_base_url,
            api_key=options.llm_api_key or config.llm_api_key,
            model=options.llm_model or config.llm_model,
            batch_size=config.batch_size,
            glossary=glossary,
        )
    raise ConfigurationError(f"Translator backend khong duoc ho tro: {backend_name}")
