# app/rate_limit.py
"""
Rate Limiting через slowapi.

Защита:
  - /auth — 10 req/min на IP
  - /cart/change, /cart/addition — 5 req/sec на user_id
  - /cart/create-order — 3 req/min на user_id
  - Общий лимит — 100 req/min на IP
"""
import logging
import os

# ⚡ Принудительно UTF-8 для чтения файлов — ДО импорта slowapi
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def get_user_or_ip(request: Request) -> str:
    """Ключ — user_id из JWT, иначе IP."""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        try:
            from app.auth import decode_token
            payload = decode_token(auth[7:], "access")
            if payload:
                return f"user:{payload['sub']}"
        except Exception:
            pass
    return f"ip:{get_remote_address(request)}"


# ⚡ Не передаём env_file — slowapi не должен читать .env
limiter = Limiter(
    key_func=get_user_or_ip,
    default_limits=["100/minute"],
    storage_uri="memory://",
)


async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Кастомный обработчик — логирует и возвращает 429."""
    logger.warning(f"Rate limit exceeded: {get_remote_address(request)} — {exc.detail}")
    return JSONResponse(
        status_code=429,
        content={
            "error": "too_many_requests",
            "detail": "Слишком много запросов. Попробуйте позже.",
        },
    )


# ─── Готовые лимиты для декораторов ───
LIMIT_AUTH = "10/minute"
LIMIT_CART_CHANGE = "5/second"
LIMIT_CART_CREATE_ORDER = "3/minute"
LIMIT_PROMO_APPLY = "10/minute"
LIMIT_WS_CONNECT = "20/minute"