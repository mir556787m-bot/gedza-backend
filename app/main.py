import asyncio
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# app/main.py
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from app.cache import (
    get_menu_cache,
    get_menu_meta,
    get_cart,
    update_cart,
    clear_cart,
    close_redis,
)
from app.scheduler import start_scheduler, stop_scheduler, refresh_menu_job
from app.models import CartUpdate, OrderCreate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Старт и остановка приложения."""
    logger.info("Запуск бэкенда Gedza MAX Bot")
    start_scheduler()
    yield
    stop_scheduler()
    await close_redis()
    logger.info("Бэкенд остановлен")


app = FastAPI(
    title="Gedza MAX Bot API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health-check ───

@app.get("/api/health")
async def health():
    meta = await get_menu_meta()
    return {
        "status": "alive",
        "menu": meta,
    }


# ─── Меню ───

@app.get("/api/menu")
async def get_menu(background: BackgroundTasks):
    """
    Мгновенная отдача из Redis.
    Если кэш пуст — запускаем парсинг в фоне и говорим клиенту 'попробуй позже'.
    """
    menu = await get_menu_cache()

    if menu:
        return {"status": "ok", "items": menu, "count": len(menu)}

    # Кэш пуст — запускаем парсинг в фоне
    logger.warning("Кэш пуст, запускаю парсинг в фоне")
    background.add_task(refresh_menu_job)

    raise HTTPException(
        status_code=202,
        detail="Меню загружается, попробуйте через 10-15 секунд",
    )


@app.post("/api/menu/refresh")
async def force_refresh(background: BackgroundTasks):
    """Принудительное обновление меню (для админки)."""
    background.add_task(refresh_menu_job)
    return {"status": "started", "message": "Парсинг запущен в фоне"}


# ─── Корзина ───

@app.get("/api/cart/{user_id}")
async def api_get_cart(user_id: int):
    cart = await get_cart(user_id)
    return {"status": "ok", "cart": cart}


@app.post("/api/cart/update")
async def api_update_cart(data: CartUpdate):
    cart = await update_cart(data.user_id, data.item_id, data.quantity)
    return {"status": "ok", "cart": cart}


@app.delete("/api/cart/{user_id}")
async def api_clear_cart(user_id: int):
    await clear_cart(user_id)
    return {"status": "cleared"}


# ─── Заказ ───

@app.post("/api/order")
async def api_create_order(order: OrderCreate, background: BackgroundTasks):
    """Создаёт заказ."""
    cart = await get_cart(order.user_id)
    if not cart:
        raise HTTPException(400, "Корзина пуста")

    menu = await get_menu_cache() or []
    menu_map = {item["id"]: item for item in menu}

    total = 0
    order_items = []
    for item_id, qty in cart.items():
        item = menu_map.get(item_id)
        if not item:
            continue
        total += item["price"] * qty
        order_items.append({
            "item_id": item_id,
            "name": item["name"],
            "price": item["price"],
            "quantity": qty,
            "sum": item["price"] * qty,
        })

    if not order_items:
        raise HTTPException(400, "Все товары из корзины недоступны")

    order_id = f"GDZ-{datetime.now().strftime('%y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    logger.info(f"Новый заказ {order_id} на {total} руб. от {order.user_id}")

    await clear_cart(order.user_id)

    background.add_task(_notify_watbot, order.user_id, order_id, total)

    return {
        "status": "ok",
        "order_id": order_id,
        "total": total,
        "items": order_items,
    }


async def _notify_watbot(user_id: int, order_id: str, total: int):
    """Отправляет webhook в WATBOT (не блокирует ответ пользователю)."""
    url = os.getenv("WATBOT_WEBHOOK_URL")
    if not url:
        return
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(url, json={
                "user_id": user_id,
                "order_id": order_id,
                "total": total,
                "status": "created",
            })
        logger.info(f"Webhook отправлен в WATBOT: {order_id}")
    except Exception as e:
        logger.error(f"Ошибка webhook: {e}")