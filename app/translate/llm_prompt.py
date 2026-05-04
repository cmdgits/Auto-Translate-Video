from __future__ import annotations

import json
import re

from app.core.exceptions import ProcessError
from app.models import TranscriptSegment


SYSTEM_PROMPT = (
    "Ban la bien dich subtitle chuyen nghiep. "
    "Hay dich tung cau sang tieng Viet tu nhien, giu dung y, giu ten rieng, "
    "giu nguyen thuat ngu ky thuat khi phu hop, khong giai thich them. "
    "Tra ve JSON array voi cac object gom id va translated_text."
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
) -> str:
    prompt_rows = [{"id": segment.id, "text": segment.text} for segment in segments]
    return json.dumps(
        {
            "source_language": source_language,
            "target_language": target_language,
            "segments": prompt_rows,
        },
        ensure_ascii=False,
    )


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
