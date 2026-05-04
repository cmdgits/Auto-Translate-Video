import httpx
from unittest.mock import patch

from app.core.exceptions import ProcessError
from app.translate.gemini_backend import GeminiTranslatorBackend
from app.translate.http_errors import format_translator_http_error
from app.translate.llm_http_backend import LLMHTTPTranslatorBackend
from app.translate.llm_prompt import parse_translation_json
from app.models import TranscriptSegment
from app.web.main import _options_from_form

HTTPX_CLIENT = httpx.Client


class MockClient:
    def __init__(self, handler) -> None:
        self.client = HTTPX_CLIENT(transport=httpx.MockTransport(handler))

    def __enter__(self):
        return self.client

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.client.close()


def test_parse_translation_json_accepts_fenced_json() -> None:
    parsed = parse_translation_json('```json\n[{"id": 1, "translated_text": "Xin chao"}]\n```')
    assert parsed[1] == "Xin chao"


def test_openai_compatible_backend_uses_bearer_header() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers.get("authorization")
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"choices": [{"message": {"content": '[{"id": 1, "translated_text": "Xin chao"}]'}}]})

    with patch.object(httpx, "Client", lambda *args, **kwargs: MockClient(handler)):
        backend = LLMHTTPTranslatorBackend("https://api.openai.com/v1", "test-key", "gpt-test", batch_size=8)
        result = backend.translate_segments([TranscriptSegment(id=1, start=0, end=1, text="Hello")], "en", "vi")

    assert result == ["Xin chao"]
    assert captured["authorization"] == "Bearer test-key"
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"


def test_gemini_backend_uses_api_key_header() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["api_key"] = request.headers.get("x-goog-api-key")
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": '[{"id": 1, "translated_text": "Tam biet"}]'}]}}]},
        )

    with patch.object(httpx, "Client", lambda *args, **kwargs: MockClient(handler)):
        backend = GeminiTranslatorBackend("gemini-key", "gemini-test", batch_size=8)
        result = backend.translate_segments([TranscriptSegment(id=1, start=0, end=1, text="Goodbye")], "en", "vi")

    assert result == ["Tam biet"]
    assert captured["api_key"] == "gemini-key"
    assert captured["url"].endswith("/models/gemini-test:generateContent")


def test_options_from_form_prefers_gemini_when_echo_has_gemini_key() -> None:
    options = _options_from_form(
        "echo",
        "tiny",
        None,
        None,
        None,
        None,
        None,
        None,
        "https://generativelanguage.googleapis.com/v1beta",
        "gemini-key",
        "gemini-test",
        None,
        None,
        False,
        False,
        None,
        None,
        None,
    )

    assert options.translator_backend == "gemini"


def test_translator_http_error_explains_quota_in_vietnamese() -> None:
    response = httpx.Response(429, json={"error": {"message": "Quota exceeded"}})

    message = format_translator_http_error("Gemini", response)

    assert "Gemini lỗi 429" in message
    assert "quota" in message
    assert "Quota exceeded" in message


def test_translator_http_error_explains_openai_insufficient_quota() -> None:
    response = httpx.Response(
        429,
        json={
            "error": {
                "message": "You exceeded your current quota",
                "type": "insufficient_quota",
                "code": "insufficient_quota",
            }
        },
    )

    message = format_translator_http_error("GPT/LLM", response)

    assert "GPT/LLM lỗi 429" in message
    assert "khác với token/session" in message
    assert "insufficient_quota" in message or "You exceeded your current quota" in message


def test_gpt_backend_raises_friendly_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "Invalid API key"}})

    with patch.object(httpx, "Client", lambda *args, **kwargs: MockClient(handler)):
        backend = LLMHTTPTranslatorBackend("https://api.openai.com/v1", "bad-key", "gpt-test", batch_size=8)
        try:
            backend.translate_segments([TranscriptSegment(id=1, start=0, end=1, text="Hello")], "en", "vi")
        except ProcessError as exc:
            assert "GPT/LLM lỗi 401" in str(exc)
        else:
            raise AssertionError("Expected ProcessError")


def test_gpt_backend_retries_429_then_succeeds() -> None:
    calls = {"count": 0}
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(429, headers={"retry-after": "0.1"}, json={"error": {"message": "Too many requests"}})
        return httpx.Response(200, json={"choices": [{"message": {"content": '[{"id": 1, "translated_text": "Xin chao"}]'}}]})

    with patch("app.translate.retry.time.sleep", lambda seconds: sleeps.append(seconds)), patch.object(
        httpx, "Client", lambda *args, **kwargs: MockClient(handler)
    ):
        backend = LLMHTTPTranslatorBackend("https://api.openai.com/v1", "test-key", "gpt-test", batch_size=8)
        result = backend.translate_segments([TranscriptSegment(id=1, start=0, end=1, text="Hello")], "en", "vi")

    assert result == ["Xin chao"]
    assert calls["count"] == 2
    assert sleeps == [0.1]


def test_gemini_backend_retries_429_then_succeeds() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] < 3:
            return httpx.Response(429, json={"error": {"message": "Quota exceeded"}})
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": '[{"id": 1, "translated_text": "Tam biet"}]'}]}}]},
        )

    with patch("app.translate.retry.time.sleep", lambda seconds: None), patch.object(
        httpx, "Client", lambda *args, **kwargs: MockClient(handler)
    ):
        backend = GeminiTranslatorBackend("gemini-key", "gemini-test", batch_size=8)
        result = backend.translate_segments([TranscriptSegment(id=1, start=0, end=1, text="Goodbye")], "en", "vi")

    assert result == ["Tam biet"]
    assert calls["count"] == 3
