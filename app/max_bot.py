# app/max_bot.py
import logging
from typing import Optional, List, Dict
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

MAX_API = settings.MAX_API_URL
BOT_USERNAME = settings.MINI_APP_NAME or "se14144667_1_bot"


async def _post(endpoint: str, payload: dict) -> dict | None:
    if not settings.MAX_BOT_TOKEN:
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
    payload: dict = {"text": text}
    if buttons:
        payload["attachments"] = [{
            "type": "inline_keyboard",
            "payload": {"buttons": buttons}
        }]
    result = await _post(f"/messages?user_id={user_id}", payload)
    return result is not None


async def send_welcome_open_app(user_id: int) -> bool:
    """Кнопка открытия Mini App без приветственного текста."""
    buttons = [[{
        "type": "open_app",
        "text": "Меню",
        "web_app": BOT_USERNAME,
    }]]
    return await send_message(user_id, "", buttons)


async def send_order_notification(user_id: int, order_id: str, total: float) -> bool:
    text = (
        f"✅ Заказ {order_id} принят!\n"
        f"Сумма: {total:.0f} ₽\n\n"
        f"Мы свяжемся с вами для подтверждения."
    )
    return await send_message(user_id, text)


async def send_status_update(user_id: int, order_id: str, status: str) -> bool:
    statuses = {
        "cooking": "👨‍🍳 Ваш заказ готовится",
        "on_the_way": "🚗 Курьер в пути",
        "delivered": "✅ Заказ доставлен",
    }
    text = f"Заказ {order_id}\n{statuses.get(status, status)}"
    return await send_message(user_id, text)