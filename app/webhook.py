# app/webhook.py
import logging
import hmac
import hashlib
from urllib.parse import parse_qsl
from fastapi import Request, HTTPException
from app.config import settings
from app.max_bot import send_welcome_open_app, send_message
from app.users import upsert_user, get_user, unsubscribe

logger = logging.getLogger(__name__)


def validate_init_data(init_data: str, bot_token: str) -> dict | None:
    if not init_data or not bot_token:
        return None
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        calculated = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(calculated, received_hash):
            return parsed
        return None
    except Exception as e:
        logger.error(f"initData error: {e}")
        return None


async def _handle_start(user_id: int, first_name: str = None, username: str = None):
    """
    Логика /start:
    ВСЕГДА показываем приветствие с кнопкой меню.
    Согласие на маркетинг запрашивается только при оформлении заказа.
    """
    await upsert_user(user_id=user_id, first_name=first_name, username=username)
    await send_welcome_open_app(user_id)


async def _process_update(data: dict) -> dict:
    update_type = data.get("update_type")
    logger.info(f"Update: {update_type}")

    if update_type == "message_created":
        msg = data.get("message", {})
        text = (msg.get("body", {}).get("text") or "").strip()
        sender = msg.get("sender", {})
        user_id = sender.get("user_id")

        if not user_id:
            return {"ok": True}

        await upsert_user(
            user_id=user_id,
            first_name=sender.get("first_name"),
            last_name=sender.get("last_name"),
            username=sender.get("username"),
        )

        if text == "/start":
            await _handle_start(
                user_id,
                first_name=sender.get("first_name"),
                username=sender.get("username"),
            )
        elif text == "/unsubscribe":
            await unsubscribe(user_id)
            await send_message(
                user_id,
                "❌ Вы отписаны от рассылок.\nЗаказы по-прежнему доступны. 🍕",
            )
        elif text == "/help":
            await send_message(
                user_id,
                "🍕 Доставка Gedza\n\n"
                "/start — меню доставки\n"
                "/unsubscribe — отписаться от рассылок\n"
                "/help — справка",
            )

    elif update_type == "bot_started":
        user = data.get("user", {})
        user_id = user.get("user_id")
        if user_id:
            await _handle_start(
                user_id,
                first_name=user.get("first_name"),
                username=user.get("username"),
            )

    elif update_type == "message_callback":
        callback = data.get("callback", {})
        payload = callback.get("payload", "")
        user = callback.get("user", {})
        user_id = user.get("user_id")

        if not user_id:
            return {"ok": True}

        logger.info(f"Callback от {user_id}: {payload}")

    return {"ok": True}


async def process_webhook(request: Request) -> dict:
    secret_header = request.headers.get("X-Max-Bot-Api-Secret", "")
    if settings.MAX_WEBHOOK_SECRET and secret_header != settings.MAX_WEBHOOK_SECRET:
        raise HTTPException(403, "Forbidden")
    data = await request.json()
    return await _process_update(data)