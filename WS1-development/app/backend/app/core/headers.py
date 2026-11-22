"""Security headers on every response.

Adapted from Guardian's `SecurityHeadersMiddleware` and tightened: no CDN scripts (Tailwind is
built at compile time), no framing at all, HSTS whenever DEBUG is off.

The interactive API docs (/api/docs) load Swagger UI from jsDelivr, so those two paths get a
slightly wider policy. Nothing else does.
"""

from __future__ import annotations

from starlette.types import ASGIApp, Message, Receive, Scope, Send

APP_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data: blob:; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)

DOCS_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "frame-ancestors 'none'"
)

DOCS_PATHS = ("/api/docs", "/api/redoc")

BASE_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}

HSTS_VALUE = "max-age=31536000; includeSubDomains"


class SecurityHeadersMiddleware:
    """Pure ASGI middleware (works for streaming and file responses too)."""

    def __init__(self, app: ASGIApp, *, hsts: bool) -> None:
        self.app = app
        self.hsts = hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        csp = DOCS_CSP if path.startswith(DOCS_PATHS) else APP_CSP

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                present = {name.lower() for name, _ in headers}
                extra = dict(BASE_HEADERS)
                extra["Content-Security-Policy"] = csp
                if self.hsts:
                    extra["Strict-Transport-Security"] = HSTS_VALUE
                for name, value in extra.items():
                    key = name.lower().encode("latin-1")
                    if key not in present:  # never override a header a route set on purpose
                        headers.append((key, value.encode("latin-1")))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)
