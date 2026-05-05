from __future__ import annotations

from typing import Any

import httpx


def _extract_error_message(payload: Any) -> str:
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            for key in ("message", "status", "code"):
                value = error.get(key)
                if value:
                    return str(value)
        if isinstance(error, str):
            return error
        for key in ("message", "detail"):
            value = payload.get(key)
            if value:
                return str(value)
    return ""


def _extract_error_code(payload: Any) -> str:
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            for key in ("code", "type", "status"):
                value = error.get(key)
                if value:
                    return str(value)
        for key in ("code", "type", "status"):
            value = payload.get(key)
            if value:
                return str(value)
    return ""


def format_translator_http_error(provider: str, response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = None
    message = _extract_error_message(payload) or response.text.strip()
    error_code = _extract_error_code(payload).lower()
    status_code = response.status_code

    if status_code == 401:
        reason = "API key không hợp lệ hoặc chưa được cấp quyền."
    elif status_code == 403:
        reason = "API key chưa có quyền dùng model này hoặc API chưa được bật."
    elif status_code == 404:
        reason = "Không tìm thấy model hoặc base URL đang sai."
    elif status_code == 429 and error_code == "insufficient_quota":
        reason = (
            "OpenAI/API báo hết quota thanh toán hoặc key chưa có billing. Đây là quota của API key, "
            "khác với token/session còn lại trong Codex, Antigravity hoặc giao diện chat."
        )
    elif status_code == 429:
        reason = (
            "Lỗi 429: Đã vượt quá rate limit hoặc quota của API key/model hiện tại. "
            "Giới hạn Gemini phụ thuộc model và tier tài khoản; hãy chờ hết thời gian retry, dùng model nhẹ hơn, "
            "tăng batch_size hoặc bật billing nếu cần xử lý nhiều video."
        )
    elif status_code >= 500:
        reason = "Máy chủ dịch đang lỗi tạm thời. Hãy thử lại sau."
    else:
        reason = "Yêu cầu dịch bị từ chối."

    detail = f" Chi tiết: {message}" if message else ""
    return f"{provider} lỗi {status_code}: {reason}{detail}"
