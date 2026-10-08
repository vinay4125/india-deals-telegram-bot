from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class HttpError(RuntimeError):
    pass


def request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: dict[str, Any] | None = None,
    form: dict[str, str] | None = None,
    timeout: int = 30,
    error_label: str | None = None,
) -> Any:
    if not url.lower().startswith("https://"):
        raise ValueError(f"Only HTTPS URLs are allowed: {url}")

    request_headers = {"Accept": "application/json", "User-Agent": "india-deals-bot/0.1"}
    request_headers.update(headers or {})
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    elif form is not None:
        from urllib.parse import urlencode

        body = urlencode(form).encode("utf-8")
        request_headers["Content-Type"] = "application/x-www-form-urlencoded"

    request = Request(url, data=body, headers=request_headers, method=method)
    display_url = error_label or url
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read()
    except HTTPError as exc:
        detail = exc.read(500).decode("utf-8", errors="replace")
        raise HttpError(
            f"{method} {display_url} failed with HTTP {exc.code}: {detail}"
        ) from exc
    except URLError as exc:
        raise HttpError(f"{method} {display_url} failed: {exc.reason}") from exc

    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise HttpError(f"{method} {display_url} returned invalid JSON") from exc
