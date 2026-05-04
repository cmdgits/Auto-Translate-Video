from __future__ import annotations

import json
import re

from app.core.exceptions import ProcessError
from app.models import TranscriptSegment


SYSTEM_PROMPT = (
    "Bạn là biên dịch phụ đề chuyên nghiệp. "
    "Hãy dịch từng câu sang tiếng Việt tự nhiên, giữ đúng ý, giữ tên riêng, không giải thích thêm. "
    "Nếu có glossary, bắt buộc ưu tiên đúng target_term cho thuật ngữ tương ứng và không tự đổi thuật ngữ kỹ thuật đã quy định. "
    "Không sửa id, không tự thêm timestamp, không làm hỏng cấu trúc JSON. "
    "Trả về JSON array với các object gồm id và translated_text."
)


def strip_json_fence(content: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", content, flags=re.DOTALL)
    if fenced:
        return fenced.group(1)
    array_match = re.search(r"(\[.*\])", content, flags=re.DOTALL)
    return array_match.group(1) if array_match else content.strip()


def build_translation_user_prompt(
    segments: list[TranscriptSegment],
    source_language: str,
    target_language: str,
    glossary: dict[str, str] | None = None,
) -> str:
    prompt_rows = [{"id": segment.id, "text": segment.text} for segment in segments]
    payload: dict[str, object] = {
        "source_language": source_language,
        "target_language": target_language,
        "segments": prompt_rows,
    }
    if glossary:
        payload["glossary"] = [
            {"source_term": source, "target_term": target} for source, target in glossary.items()
        ]
        payload["glossary_instruction"] = "Ưu tiên dùng đúng target_term cho các thuật ngữ trong glossary."
    return json.dumps(payload, ensure_ascii=False)


def parse_translation_json(content: str) -> dict[int, str]:
    try:
        parsed = json.loads(strip_json_fence(content))
    except json.JSONDecodeError as exc:
        raise ProcessError("Khong parse duoc phan hoi JSON tu LLM translator.") from exc
    if not isinstance(parsed, list):
        raise ProcessError("Phan hoi LLM translator khong phai JSON array.")

    translated_map: dict[int, str] = {}
    for item in parsed:
        if not isinstance(item, dict):
            continue
        try:
            translated_map[int(item["id"])] = str(item["translated_text"]).strip()
        except (KeyError, TypeError, ValueError):
            continue
    return translated_map
