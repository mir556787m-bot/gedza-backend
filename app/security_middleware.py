# app/security_middleware.py
"""
Заголовки безопасности для всех ответов.

Защита от:
  - XSS (Content-Security-Policy)
  - Clickjacking (X-Frame-Options)
  - MIME-sniffing (X-Content-Type-Options)
  - Утечки Referer (Referrer-Policy)
  - Небезопасных функций браузера (Permissions-Policy)
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # Разрешаем MAX Messenger встраивать наш Mini App в iframe
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://st.max.ru; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' wss: https:; "
            "frame-ancestors https://max.ru https://*.max.ru; "
            "base-uri 'self'; "
            "form-action 'self';"
        )

        # Остальные заголовки
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "ALLOW-FROM https://max.ru"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(self), camera=(), microphone=(), payment=(self)"
        )
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

        return response