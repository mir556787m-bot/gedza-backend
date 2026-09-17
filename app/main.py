# app/main.py
import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Header
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.cache import (
    get_menu_cache, get_menu_meta, get_cart,
    update_cart, clear_cart, close_redis,
)
from app.scheduler import start_scheduler, stop_scheduler, refresh_menu_job
from app.models import CartUpdate, OrderCreate
from app.max_bot import send_order_notification
from app.database import init_db, close_pool
from app.users import get_user
from app.orders import create_order, get_user_orders
from app.broadcast import broadcast_to_all
from app.webhook import process_webhook, validate_init_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Запуск бэкенда Gedza MAX Bot")
    try:
        await init_db()
        logger.info("Database initialized: 5 tables ready")
    except Exception as e:
        logger.error(f"Database init failed: {e}")
    start_scheduler()
    from app.poller import start_polling, stop_polling
    start_polling()
    logger.info("Long Polling активен")
    yield
    await stop_polling()
    stop_scheduler()
    await close_redis()
    await close_pool()
    logger.info("Бэкенд остановлен")


app = FastAPI(title="Gedza MAX Bot API", version="4.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    meta = await get_menu_meta()
    return {"status": "alive", "menu": meta}


@app.get("/api/menu")
async def get_menu(background: BackgroundTasks):
    menu = await get_menu_cache()
    if menu:
        return {"status": "ok", "items": menu, "count": len(menu)}
    background.add_task(refresh_menu_job)
    raise HTTPException(202, "Меню загружается, попробуйте через 10-15 секунд")


@app.post("/api/menu/refresh")
async def force_refresh(background: BackgroundTasks):
    background.add_task(refresh_menu_job)
    return {"status": "started"}


@app.get("/api/cart/{user_id}")
async def api_get_cart(user_id: int):
    return {"status": "ok", "cart": await get_cart(user_id)}


@app.post("/api/cart/update")
async def api_update_cart(data: CartUpdate):
    cart = await update_cart(data.user_id, data.item_id, data.quantity)
    return {"status": "ok", "cart": cart}


@app.delete("/api/cart/{user_id}")
async def api_clear_cart(user_id: int):
    await clear_cart(user_id)
    return {"status": "cleared"}


@app.post("/api/order")
async def api_create_order(order: OrderCreate, background: BackgroundTasks):
    cart = await get_cart(order.user_id)
    if not cart:
        raise HTTPException(400, "Корзина пуста")
    menu = await get_menu_cache() or []
    menu_map = {item["id"]: item for item in menu}
    total = 0.0
    order_items = []
    for item_id, qty in cart.items():
        item = menu_map.get(item_id)
        if not item:
            continue
        total += item["price"] * qty
        order_items.append({
            "item_id": item_id, "name": item["name"],
            "price": item["price"], "quantity": qty,
            "sum": item["price"] * qty,
        })
    if not order_items:
        raise HTTPException(400, "Все товары недоступны")
    order_id = f"GDZ-{datetime.now().strftime('%y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    logger.info(f"Новый заказ {order_id} на {total} руб. от {order.user_id}")
    await create_order(order_id, order.user_id, total, order_items,
                       order.address, order.phone, order.comment)
    await clear_cart(order.user_id)
    background.add_task(send_order_notification, order.user_id, order_id, total)
    return {"status": "ok", "order_id": order_id, "total": total, "items": order_items}


@app.get("/api/orders/{user_id}")
async def api_user_orders(user_id: int):
    orders = await get_user_orders(user_id)
    return {"status": "ok", "orders": orders}


@app.get("/api/me")
async def api_me(x_max_init_data: str = Header(None)):
    if not x_max_init_data:
        raise HTTPException(401, "Missing X-Max-Init-Data")
    user_data = validate_init_data(x_max_init_data, settings.MAX_BOT_TOKEN)
    if not user_data:
        raise HTTPException(401, "Invalid initData")
    return {"status": "ok", "user": user_data}


@app.post("/webhook/max")
async def max_webhook(request: Request):
    return await process_webhook(request)


@app.post("/api/admin/broadcast")
async def admin_broadcast(data: dict, background: BackgroundTasks):
    if data.get("secret") != settings.ADMIN_SECRET:
        raise HTTPException(403, "Forbidden")
    text = data.get("text", "").strip()
    if not text:
        raise HTTPException(400, "text обязателен")
    background.add_task(
        broadcast_to_all,
        text=text,
        button_text=data.get("button_text"),
        button_url=data.get("button_url"),
        only_consented=data.get("is_promo", True),
    )
    return {"status": "started"}
