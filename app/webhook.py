# app/webhook.py
import logging
import hmac
import hashlib
from urllib.parse import parse_qsl
from fastapi import Request, HTTPException
from app.config import settings
from app.max_bot import send_welcome, send_message
from app.users import upsert_user, give_consent, unsubscribe

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
        logger.warning("initData validation failed")
        return None
    except Exception as e:
        logger.error(f"initData error: {e}")
        return None


async def _process_update(data: dict) -> dict:
    """Обрабатывает одно событие от MAX (webhook или polling)."""
    update_type = data.get("update_type")
    logger.info(f"Update: {update_type}")

    if update_type == "message_created":
        msg = data.get("message", {})
        text = msg.get("body", {}).get("text", "")
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

        if text.strip() == "/start":
            await send_welcome(user_id)
        elif text.strip() == "/unsubscribe":
            await unsubscribe(user_id)
            await send_message(user_id, "Вы отписались от рассылок. Заказ оформить всё ещё можно! 🍕")

    elif update_type == "bot_started":
        user = data.get("user", {})
        user_id = user.get("user_id")
        if user_id:
            await upsert_user(user_id=user_id, first_name=user.get("first_name"))
            await send_welcome(user_id)

    elif update_type == "message_callback":
        callback = data.get("callback", {})
        payload = callback.get("payload", "")
        user = callback.get("user", {})
        user_id = user.get("user_id")
        if payload == "consent_give" and user_id:
            await give_consent(user_id)
            await send_message(user_id, "Спасибо! Теперь вы будете получать наши акции. 🎉")

    return {"ok": True}


async def process_webhook(request: Request) -> dict:
    """Обрабатывает входящий webhook от MAX (для продакшна с VPS)."""
    secret_header = request.headers.get("X-Max-Bot-Api-Secret", "")
    if settings.MAX_WEBHOOK_SECRET and secret_header != settings.MAX_WEBHOOK_SECRET:
        raise HTTPException(403, "Forbidden")
    data = await request.json()
    return await _process_update(data)
