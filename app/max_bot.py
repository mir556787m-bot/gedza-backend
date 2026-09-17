# app/max_bot.py
import logging
from typing import Optional, List, Dict
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

MAX_API = settings.MAX_API_URL

# Кэш информации о боте (username, user_id) — запрашивается один раз
_bot_info_cache: Optional[dict] = None


async def get_bot_info() -> dict:
    """
    Получает информацию о боте через GET /me.
    Возвращает dict с ключами user_id, username, first_name.
    """
    global _bot_info_cache
    if _bot_info_cache is not None:
        return _bot_info_cache

    url = f"{MAX_API}/me"
    headers = {"Authorization": settings.MAX_BOT_TOKEN}
    try:
        async with httpx.AsyncClient(timeout=10, verify=False) as client:
            r = await client.get(url, headers=headers)
            if r.status_code == 200:
                _bot_info_cache = r.json()
                logger.info(
                    f"Bot info: user_id={_bot_info_cache.get('user_id')}, "
                    f"username={_bot_info_cache.get('username')}"
                )
                return _bot_info_cache
            logger.error(f"get_bot_info {r.status_code}: {r.text[:300]}")
            return {}
    except Exception as e:
        logger.error(f"get_bot_info exception: {e}")
        return {}


async def _post(endpoint: str, payload: dict) -> dict | None:
    """Базовый POST-запрос к MAX Bot API."""
    if not settings.MAX_BOT_TOKEN:
        logger.warning("MAX_BOT_TOKEN не задан")
        return None
    url = f"{MAX_API}{endpoint}"
    headers = {
        "Authorization": settings.MAX_BOT_TOKEN,
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            r = await client.post(url, json=payload, headers=headers)
            if r.status_code == 200:
                return r.json()
            logger.error(f"MAX API {r.status_code}: {r.text[:300]}")
            return None
    except Exception as e:
        logger.error(f"MAX API error: {e}")
        return None


async def send_message(
    user_id: int,
    text: str,
    buttons: Optional[List[List[Dict]]] = None,
) -> bool:
    """Отправляет сообщение пользователю через MAX Bot API."""
    payload: dict = {"text": text}
    if buttons:
        payload["attachments"] = [{
            "type": "inline_keyboard",
            "payload": {"buttons": buttons}
        }]
    result = await _post(f"/messages?user_id={user_id}", payload)
    return result is not None


async def send_welcome(user_id: int) -> bool:
    """
    Приветствие с нативной кнопкой open_app.
    Открывает Mini App ВНУТРИ MAX.

    ВАЖНО: параметр web_app = username бота (не URL!),
    параметр contact_id = user_id бота.
    """
    bot_info = await get_bot_info()
    bot_username = bot_info.get("username")
    bot_user_id = bot_info.get("user_id")

    text = (
        "Добро пожаловать в доставку Gedza! 🍕\n\n"
        "Нажмите кнопку ниже, чтобы открыть меню:"
    )

    # Если удалось получить данные бота — отправляем open_app-кнопку
    if bot_username and bot_user_id:
        buttons = [[{
            "type": "open_app",
            "text": "🍕 Открыть меню доставки",
            "web_app": bot_username,      # username бота, не URL
            "contact_id": bot_user_id,    # user_id бота
        }]]
        return await send_message(user_id, text, buttons)

    # Fallback: если не удалось — отправляем ссылку в тексте
    logger.warning("Bot info unavailable, falling back to text link")
    fallback_text = (
        f"{text}\n"
        f"{settings.MINI_APP_URL}"
    )
    return await send_message(user_id, fallback_text)


async def send_order_notification(user_id: int, order_id: str, total: float) -> bool:
    """Уведомление о принятом заказе."""
    text = (
        f"✅ Заказ {order_id} принят!\n"
        f"Сумма: {total:.0f} ₽\n\n"
        f"Мы свяжемся с вами для подтверждения."
    )
    return await send_message(user_id, text)


async def send_status_update(user_id: int, order_id: str, status: str) -> bool:
    """Обновление статуса заказа."""
    statuses = {
        "cooking": "👨‍🍳 Ваш заказ готовится",
        "on_the_way": "🚗 Курьер в пути",
        "delivered": "✅ Заказ доставлен",
    }
    text = f"Заказ {order_id}\n{statuses.get(status, status)}"
    return await send_message(user_id, text)


async def set_webhook(webhook_url: str, secret: str) -> bool:
    """Устанавливает webhook (для продакшна с VPS)."""
    payload = {
        "url": webhook_url,
        "update_types": ["message_created", "bot_started", "message_callback"],
        "secret": secret,
    }
    result = await _post("/subscriptions", payload)
    return result is not None


async def delete_webhook() -> bool:
    """Удаляет подписку на webhook."""
    url = f"{MAX_API}/subscriptions"
    headers = {"Authorization": settings.MAX_BOT_TOKEN}
    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            r = await client.delete(url, headers=headers)
            return r.status_code == 200
    except Exception as e:
        logger.error(f"Delete webhook error: {e}")
        return False