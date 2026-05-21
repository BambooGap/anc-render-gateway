from __future__ import annotations

from fastapi import Request

REQUEST_ID_HEADER = "X-Request-ID"


def get_request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str) and request_id:
        return request_id
    return "unknown"
