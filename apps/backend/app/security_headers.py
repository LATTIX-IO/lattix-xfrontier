from __future__ import annotations

from typing import Any


SECURITY_HEADERS: dict[str, str] = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "content-security-policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
    "referrer-policy": "no-referrer",
    "permissions-policy": "camera=(), microphone=(), geolocation=(), browsing-topics=()",
    "x-permitted-cross-domain-policies": "none",
    "cross-origin-opener-policy": "same-origin",
}


def apply_security_headers(response: Any) -> Any:
    for header, value in SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)
    return response
