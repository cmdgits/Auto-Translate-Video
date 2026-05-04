from __future__ import annotations

import time

import httpx


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def _retry_delay_sec(response: httpx.Response, attempt: int) -> float:
    retry_after = response.headers.get("retry-after")
    if retry_after:
        try:
            return min(max(float(retry_after), 0.0), 30.0)
        except ValueError:
            pass
            
    # Try to parse 'Please retry in 9.75s' from Gemini error body
    try:
        import re
        body = response.text
        match = re.search(r"retry in ([\d\.]+)s", body)
        if match:
            return min(max(float(match.group(1)) + 0.5, 0.0), 30.0)
    except Exception:
        pass
        
    return min(3.0 ** (attempt - 1) + 2.0, 30.0)


def post_with_retry(client: httpx.Client, url: str, *, max_attempts: int = 5, **kwargs) -> httpx.Response:
    response: httpx.Response | None = None
    for attempt in range(1, max_attempts + 1):
        response = client.post(url, **kwargs)
        if response.status_code not in RETRYABLE_STATUS_CODES or attempt >= max_attempts:
            return response
        time.sleep(_retry_delay_sec(response, attempt))
    if response is None:  # pragma: no cover - defensive guard
        raise RuntimeError("Khong gui duoc yeu cau dich.")
    return response
