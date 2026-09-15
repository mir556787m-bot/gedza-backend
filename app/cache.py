# app/cache.py
import json
import os
import logging
from typing import Optional
from datetime import datetime

import redis.asyncio as redis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
MENU_CACHE_TTL = int(os.getenv("MENU_CACHE_TTL", "3600"))

_redis: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """Ленивая инициализация Redis-клиента (singleton)."""
    global _redis
    if _redis is None:
        _redis = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            health_check_interval=30,
        )
    return _redis


async def close_redis():
    """Закрываем соединение при выключении приложения."""
    global _redis
    if _redis:
        await _redis.close()
        _redis = None


# ─── Меню ───

async def get_menu_cache() -> Optional[list]:
    """Мгновенно читает меню из Redis. Возвращает None, если кэша нет."""
    try:
        r = await get_redis()
        raw = await r.get("menu:full")
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.error(f"Redis read error: {e}")
    return None


async def set_menu_cache(menu: list, ttl: int = MENU_CACHE_TTL) -> bool:
    """Кладёт меню в Redis с TTL."""
    try:
        r = await get_redis()
        await r.setex("menu:full", ttl, json.dumps(menu, ensure_ascii=False))
        await r.set("menu:updated_at", datetime.utcnow().isoformat())
        logger.info(f"Меню сохранено в Redis: {len(menu)} позиций")
        return True
    except Exception as e:
        logger.error(f"Redis write error: {e}")
        return False


async def get_menu_meta() -> dict:
    """Метаданные кэша: когда обновлялся, сколько позиций."""
    try:
        r = await get_redis()
        updated_at = await r.get("menu:updated_at")
        raw = await r.get("menu:full")
        count = len(json.loads(raw)) if raw else 0
        ttl = await r.ttl("menu:full")
        return {
            "updated_at": updated_at,
            "items_count": count,
            "ttl_seconds": ttl,
            "is_fresh": ttl > 0,
        }
    except Exception as e:
        logger.error(f"Redis meta error: {e}")
        return {"updated_at": None, "items_count": 0, "ttl_seconds": -1, "is_fresh": False}


# ─── Блокировка парсинга ───

async def acquire_parse_lock(ttl: int = 120) -> bool:
    """Пытается взять распределённую блокировку на парсинг."""
    try:
        r = await get_redis()
        result = await r.set("menu:parse_lock", "1", nx=True, ex=ttl)
        return bool(result)
    except Exception as e:
        logger.error(f"Redis lock error: {e}")
        return False


async def release_parse_lock():
    try:
        r = await get_redis()
        await r.delete("menu:parse_lock")
    except Exception as e:
        logger.error(f"Redis unlock error: {e}")


# ─── Корзина ───

async def get_cart(user_id: int) -> dict:
    try:
        r = await get_redis()
        cart = await r.hgetall(f"cart:{user_id}")
        return {k: int(v) for k, v in cart.items()}
    except Exception as e:
        logger.error(f"Redis cart read error: {e}")
        return {}


async def update_cart(user_id: int, item_id: str, delta: int) -> dict:
    try:
        r = await get_redis()
        key = f"cart:{user_id}"
        current = int(await r.hget(key, item_id) or 0)
        new_qty = current + delta

        if new_qty <= 0:
            await r.hdel(key, item_id)
        else:
            await r.hset(key, item_id, new_qty)

        await r.expire(key, 86400 * 7)
        return await get_cart(user_id)
    except Exception as e:
        logger.error(f"Redis cart write error: {e}")
        return {}


async def clear_cart(user_id: int):
    try:
        r = await get_redis()
        await r.delete(f"cart:{user_id}")
    except Exception as e:
        logger.error(f"Redis cart clear error: {e}")