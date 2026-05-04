from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path


def parse_glossary_text(glossary_text: str | None) -> dict[str, str]:
    if not glossary_text:
        return {}
    glossary: dict[str, str] = {}
    for raw_line in glossary_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        source = ""
        target = ""
        if "," in line:
            try:
                row = next(csv.reader(io.StringIO(line)))
                if len(row) >= 2:
                    source, target = row[0], row[1]
            except csv.Error:
                source, target = "", ""
        if not source:
            for separator in ("=>", "=", "|"):
                if separator in line:
                    source, target = line.split(separator, 1)
                    break
        source = source.strip()
        target = target.strip()
        if source and target:
            glossary[source] = target
    return glossary


def parse_glossary_json_file(path: str | Path | None) -> dict[str, str]:
    if not path:
        return {}
    glossary_path = Path(path)
    if not glossary_path.exists():
        return {}
    payload = json.loads(glossary_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        raw_items = payload.get("terms", payload)
        if isinstance(raw_items, dict):
            return {str(source).strip(): str(target).strip() for source, target in raw_items.items() if str(source).strip() and str(target).strip()}
        payload = raw_items
    if isinstance(payload, list):
        glossary: dict[str, str] = {}
        for item in payload:
            if not isinstance(item, dict):
                continue
            source = item.get("source") or item.get("source_term") or item.get("term") or item.get("from")
            target = item.get("target") or item.get("target_term") or item.get("translation") or item.get("to")
            if source and target:
                glossary[str(source).strip()] = str(target).strip()
        return glossary
    return {}


def load_glossary(glossary_text: str | None = None, glossary_json_path: str | Path | None = None) -> dict[str, str]:
    return {**parse_glossary_json_file(glossary_json_path), **parse_glossary_text(glossary_text)}


def apply_glossary_replacements(text: str, glossary: dict[str, str]) -> str:
    translated = text
    for source, target in sorted(glossary.items(), key=lambda item: len(item[0]), reverse=True):
        pattern = re.compile(rf"(?<!\w){re.escape(source)}(?!\w)", flags=re.IGNORECASE)
        translated = pattern.sub(target, translated)
    return translated
