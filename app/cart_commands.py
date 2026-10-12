# app/cart_commands.py
"""
Команды для корзины — имитация SellKit API.
Единая точка для изменения состояния корзины через ID промокодов.

⚡ Эксклюзивная логика:
   Пользователь может применить только ОДИН промокод к заказу.
   Клик по новому промокоду заменяет ранее выбранный.
   Клик по уже выбранному — снимает выбор.

⚡ Кэширование:
   get_active_promos() кэшируется в Redis на 30 секунд.
"""
import json
import logging
from typing import Dict, Any, List

from app.cache import get_redis
from app.database import get_pool

logger = logging.getLogger(__name__)

PROMOS_CACHE_TTL = 30


# ═══════════════════════════════════════════
#  КОМАНДЫ
# ═══════════════════════════════════════════

async def set_promos(user_id: int, promos_ids_string: str) -> Dict[str, Any]:
    """Устанавливает активные промокоды по строке ID."""
    r = await get_redis()
    key = f"cart:promos:{user_id}"

    if not promos_ids_string or not promos_ids_string.strip():
        await r.delete(key)
        await _invalidate_promos_cache(user_id)
        logger.info(f"[user {user_id}] Промокоды очищены")
        return {"success": True, "promosIdsString": ""}

    cleaned = ",".join(filter(None, [x.strip() for x in promos_ids_string.split(",")]))
    ids = [int(x) for x in cleaned.split(",") if x.isdigit()]

    if not ids:
        await r.delete(key)
        await _invalidate_promos_cache(user_id)
        return {"success": True, "promosIdsString": ""}

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id FROM promocodes WHERE id = ANY($1::int[]) AND is_active = TRUE",
            ids,
        )

    valid_ids = {str(r["id"]) for r in rows}
    valid_string = ",".join(sorted(valid_ids, key=int))

    if not valid_string:
        await r.delete(key)
        await _invalidate_promos_cache(user_id)
        return {"success": False, "promosIdsString": "", "message": "Промокоды не найдены"}

    await r.set(key, valid_string, ex=86400 * 7)
    await _invalidate_promos_cache(user_id)
    logger.info(f"[user {user_id}] Промокоды установлены: {valid_string}")

    return {"success": True, "promosIdsString": valid_string}


async def get_promos_ids(user_id: int) -> str:
    """Возвращает строку активных промокодов (или пустую)."""
    r = await get_redis()
    return await r.get(f"cart:promos:{user_id}") or ""


async def get_active_promos(user_id: int) -> List[dict]:
    """
    Возвращает полные данные активных промокодов из БД.
    ⚡ Кэшируется в Redis на 30 секунд.
    """
    r = await get_redis()
    cache_key = f"promos:active:{user_id}"

    try:
        cached = await r.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Redis promos cache read error: {e}")

    ids_str = await get_promos_ids(user_id)
    if not ids_str:
        return []

    ids = [int(x) for x in ids_str.split(",") if x.isdigit()]
    if not ids:
        return []

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, code, title, description, tag, percent, discount, "
            "       sale_type, promocode_type, delivery_types, category_name, "
            "       applies_to_category_only, gift_name, gift_picture "
            "FROM promocodes WHERE id = ANY($1::int[]) AND is_active = TRUE "
            "ORDER BY id",
            ids,
        )
    result = [dict(r) for r in rows]

    try:
        await r.setex(
            cache_key,
            PROMOS_CACHE_TTL,
            json.dumps(result, ensure_ascii=False, default=str),
        )
    except Exception as e:
        logger.warning(f"Redis promos cache write error: {e}")

    return result


async def _invalidate_promos_cache(user_id: int):
    """Сбрасывает кэш активных промокодов."""
    try:
        r = await get_redis()
        await r.delete(f"promos:active:{user_id}")
    except Exception as e:
        logger.warning(f"Redis promos cache invalidate error: {e}")


async def toggle_promo(user_id: int, promo_id: int) -> Dict[str, Any]:
    """
    ⚡ Эксклюзивное переключение промокода.

    Правила:
      - Клик по НЕвыбранному промокоду → выбрать ТОЛЬКО его
      - Клик по ВЫБРАННОМУ промокоду → снять выбор
    """
    current = await get_promos_ids(user_id)
    current_ids = set(current.split(",")) if current else set()
    pid = str(promo_id)

    if pid in current_ids:
        current_ids.discard(pid)
        action = "removed"
    else:
        current_ids = {pid}
        action = "added"

    new_string = ",".join(
        sorted(current_ids, key=lambda x: int(x) if x.isdigit() else 0)
    )

    logger.info(
        f"[user {user_id}] toggle_promo: id={promo_id}, "
        f"action={action}, new_string='{new_string}'"
    )

    result = await set_promos(user_id, new_string)
    result["action"] = action
    result["toggledId"] = promo_id
    return result


async def clear_promos(user_id: int) -> Dict[str, Any]:
    """Очищает все промокоды."""
    return await set_promos(user_id, "")