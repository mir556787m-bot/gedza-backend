# app/main.py
import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
import uuid

from fastapi import FastAPI, HTTPException, BackgroundTasks, Header, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Windows ProactorEventLoop для asyncpg/playwright
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from app.config import settings
from app.cache import (
    get_menu_cache, get_menu_meta, get_cart,
    update_cart, clear_cart, close_redis,
)
from app.scheduler import start_scheduler, stop_scheduler, refresh_menu_job
from app.models import CartUpdate, OrderCreate
from app.max_bot import send_order_notification
from app.database import (
    init_db, close_pool,
    upsert_session, get_session,
    get_user_addresses, add_user_address,
    delete_user_address, set_default_address,
    set_payment_type, get_payment_type,
    set_order_time, get_order_time,
    register_user, get_user_profile,
    get_pool,
)
from app.users import get_user, give_consent, decline_consent
from app.orders import create_order, get_user_orders
from app.broadcast import broadcast_to_all
from app.webhook import process_webhook
from app.restaurants import (
    get_restaurants_with_distance,
    get_restaurant_by_id,
    calc_delivery_time,
)
from app.delivery import get_delivery_conditions, get_available_slots
from app.cart_manager import (
    build_cart_response,
    update_cart_item,
    clear_cart as clear_cart_sk,
)

# ─── Новые модули (безопасность + WS) ───
from app.auth import (
    validate_init_data as validate_init_data_strict,
    extract_user_id,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
)
from app.rate_limit import (
    limiter,
    rate_limit_handler,
    LIMIT_AUTH,
)
from app.ws_tracker import ws_router, notify_order_status_change
from app.security_middleware import SecurityHeadersMiddleware

from app.cart_endpoints import router as cart_router

from slowapi.errors import RateLimitExceeded


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Запуск бэкенда Gedza MAX Bot")
    await init_db()
    logger.info("Database initialized")

    # ─── Seed справочников ───
    try:
        from app.database import seed_wheel_prizes, seed_promocodes
        await seed_wheel_prizes()
        await seed_promocodes()
        logger.info("Справочники засеяны")
    except Exception as e:
        logger.error(f"Ошибка seed: {e}")

    start_scheduler()
    logger.info("Планировщик запущен")

    from app.poller import start_polling, stop_polling
    start_polling()
    logger.info("Long Polling активен")

    yield

    logger.info("Бэкенд остановлен")
    await stop_polling()
    stop_scheduler()
    await close_redis()
    await close_pool()


app = FastAPI(title="Gedza MAX Bot", lifespan=lifespan)

# ─── Middleware (порядок важен!) ───

# 1. Заголовки безопасности
app.add_middleware(SecurityHeadersMiddleware)

# 2. CORS — ограниченный whitelist
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://max.ru",
        "https://web.max.ru",
        "https://217.60.186.161.nip.io",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Max-Init-Data"],
    max_age=3600,
)

# 3. Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# 4. Роутеры
app.include_router(cart_router)
app.include_router(ws_router)


# ═══════════════════════════════════════════
#  HEALTH
# ═══════════════════════════════════════════

@app.get("/api/health")
async def api_health():
    meta = await get_menu_meta()
    return {"status": "alive", "menu": meta}


# ═══════════════════════════════════════════
#  AUTH — обмен initData на JWT
# ═══════════════════════════════════════════

class AuthRequest(BaseModel):
    init_data: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    user_id: int
    expires_in: int = 900


@app.post("/api/v1/auth", response_model=AuthResponse)
@limiter.limit(LIMIT_AUTH)
async def auth_endpoint(request: Request, payload: AuthRequest):
    """
    Принимает initData от MAX Bridge, валидирует HMAC-SHA256,
    возвращает JWT access + refresh.
    """
    parsed = validate_init_data_strict(payload.init_data)
    if not parsed:
        raise HTTPException(401, "Invalid initData signature")

    user_id = extract_user_id(parsed)
    if not user_id:
        raise HTTPException(401, "user_id not found in initData")

    # Сохраняем/обновляем пользователя
    try:
        from app.database import upsert_user
        user_info = {}
        try:
            import json
            user_info = json.loads(parsed.get("user", "{}"))
        except Exception:
            pass
        await upsert_user(
            user_id,
            username=user_info.get("username"),
            first_name=user_info.get("first_name"),
            last_name=user_info.get("last_name"),
        )
    except Exception as e:
        logger.warning(f"upsert_user failed: {e}")

    return AuthResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
        user_id=user_id,
    )


class RefreshRequest(BaseModel):
    refresh_token: str


@app.post("/api/v1/auth/refresh", response_model=AuthResponse)
@limiter.limit("30/minute")
async def refresh_endpoint(request: Request, payload: RefreshRequest):
    """Обновляет access по refresh."""
    decoded = decode_token(payload.refresh_token, expected_type="refresh")
    if not decoded:
        raise HTTPException(401, "Invalid refresh token")
    try:
        user_id = int(decoded["sub"])
    except (KeyError, ValueError):
        raise HTTPException(401, "Malformed refresh token")
    return AuthResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
        user_id=user_id,
    )


@app.get("/api/v1/me")
async def me_endpoint(user_id: int = Depends(get_current_user)):
    """Проверка JWT."""
    profile = await get_user_profile(user_id)
    return {"user_id": user_id, "profile": profile}


# ═══════════════════════════════════════════
#  MENU
# ═══════════════════════════════════════════

@app.get("/api/menu")
async def api_menu():
    menu = await get_menu_cache()
    if not menu:
        asyncio.create_task(refresh_menu_job())
        raise HTTPException(202, "Loading")
    return {"items": menu}


@app.post("/api/menu/refresh")
async def api_menu_refresh():
    await refresh_menu_job()
    menu = await get_menu_cache()
    return {"status": "ok", "items_count": len(menu) if menu else 0}


# ═══════════════════════════════════════════
#  LEGACY CART
# ═══════════════════════════════════════════

@app.get("/api/cart/{user_id}")
async def api_cart_get_legacy(user_id: int):
    cart = await get_cart(user_id)
    return {"cart": cart}


@app.post("/api/cart/update")
async def api_cart_update(data: CartUpdate):
    cart = await update_cart(data.user_id, data.item_id, data.quantity)
    return {"status": "ok", "cart": cart}


# ═══════════════════════════════════════════
#  ORDER (legacy)
# ═══════════════════════════════════════════

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
            "item_id": item_id,
            "name": item["name"],
            "price": item["price"],
            "quantity": qty,
            "sum": item["price"] * qty,
        })

    if not order_items:
        raise HTTPException(400, "Все товары недоступны")

    order_id = f"GDZ-{datetime.now().strftime('%y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    logger.info(f"Новый заказ {order_id} на {total} руб. от {order.user_id}")

    await create_order(
        order_id, order.user_id, total, order_items,
        order.address, order.phone, order.comment,
    )

    if order.marketing_consent:
        await give_consent(order.user_id)
    else:
        await decline_consent(order.user_id)

    await clear_cart(order.user_id)
    background.add_task(send_order_notification, order.user_id, order_id, total)

    return {
        "status": "ok",
        "order_id": order_id,
        "total": total,
        "items": order_items,
    }


@app.get("/api/orders/{user_id}")
async def api_orders(user_id: int, limit: int = 10):
    orders = await get_user_orders(user_id, limit)
    return {"orders": orders}


# ═══════════════════════════════════════════
#  SESSION / ADDRESSES
# ═══════════════════════════════════════════

class SessionInit(BaseModel):
    delivery_type: str = "delivery"
    address: str = ""
    address_details: Optional[dict] = None


class AddressAdd(BaseModel):
    address: str
    address_details: Optional[dict] = None
    is_default: bool = False


@app.post("/api/v1/session/init")
async def api_session_init(
    data: SessionInit,
    user_id: int = Depends(get_current_user),
):
    """
    При смене типа доставки — сбрасываем промокоды, чтобы фронт
    переприменил подходящие (Самовывоз только для pickup).
    """
    from app.cart_commands import clear_promos

    prev = await get_session(user_id)
    if prev and prev.get("delivery_type") != data.delivery_type:
        try:
            await clear_promos(user_id)
            logger.info(f"[user {user_id}] промокоды сброшены при смене доставки")
        except Exception as e:
            logger.warning(f"clear_promos failed: {e}")

    session = await upsert_session(
        user_id, data.delivery_type,
        data.address, data.address_details,
    )
    return {"status": "ok", "session": session}


@app.get("/api/v1/session/me")
async def api_session_me(user_id: int = Depends(get_current_user)):
    session = await get_session(user_id)
    return {"status": "ok", "session": session}


@app.get("/api/v1/user/addresses")
async def api_get_addresses(user_id: int = Depends(get_current_user)):
    addresses = await get_user_addresses(user_id)
    return {"status": "ok", "addresses": addresses}


@app.post("/api/v1/user/addresses")
async def api_add_address(
    data: AddressAdd,
    user_id: int = Depends(get_current_user),
):
    address = await add_user_address(
        user_id, data.address,
        data.address_details, data.is_default,
    )
    return {"status": "ok", "address": address}


@app.delete("/api/v1/user/addresses/{address_id}")
async def api_delete_address(
    address_id: int,
    user_id: int = Depends(get_current_user),
):
    ok = await delete_user_address(address_id)
    return {"status": "ok" if ok else "not_found"}


@app.post("/api/v1/user/addresses/{address_id}/default")
async def api_set_default_address(
    address_id: int,
    user_id: int = Depends(get_current_user),
):
    ok = await set_default_address(user_id, address_id)
    return {"status": "ok" if ok else "not_found"}


# ═══════════════════════════════════════════
#  USER REGISTRATION / PROFILE
# ═══════════════════════════════════════════

class RegisterUser(BaseModel):
    name: str = ''
    phone: str
    address: str
    address_details: Optional[dict] = None
    legal_agreed: bool = True


@app.post("/api/v1/user/register")
async def api_user_register(
    data: RegisterUser,
    user_id: int = Depends(get_current_user),
):
    digits = "".join(filter(str.isdigit, data.phone))
    if len(digits) < 11:
        raise HTTPException(400, "Некорректный номер телефона")
    if not data.address.strip():
        raise HTTPException(400, "Укажите адрес доставки")
    if not data.legal_agreed:
        raise HTTPException(400, "Необходимо согласие на обработку данных")

    profile = await register_user(
        user_id,
        data.phone,
        data.address.strip(),
        data.legal_agreed,
        data.name.strip(),
        data.address_details,
    )

    # Сохраняем адрес в user_addresses
    try:
        existing = await get_user_addresses(user_id)
        already = any(
            a["address"].strip().lower() == data.address.strip().lower()
            for a in existing
        )
        if not already:
            await add_user_address(
                user_id,
                data.address.strip(),
                data.address_details,
                is_default=True,
            )
    except Exception as e:
        logger.warning(f"user_addresses save failed: {e}")

    return {"status": "ok", "profile": profile}


@app.get("/api/v1/user/profile")
async def api_user_profile(user_id: int = Depends(get_current_user)):
    profile = await get_user_profile(user_id)
    if not profile:
        return {"status": "ok", "profile": None, "legal_agreed": False}
    return {"status": "ok", "profile": profile}


# ═══════════════════════════════════════════
#  RESTAURANTS
# ═══════════════════════════════════════════

@app.get("/api/v1/restaurants/list")
async def api_restaurants_list(lat: float = None, lon: float = None):
    restaurants = get_restaurants_with_distance(lat, lon)
    return {"status": "ok", "restaurants": restaurants}


@app.get("/api/v1/restaurants/{restaurant_id}")
async def api_restaurant_get(restaurant_id: int):
    r = get_restaurant_by_id(restaurant_id)
    if not r:
        raise HTTPException(404, "Restaurant not found")
    return {"status": "ok", "restaurant": r}


# ═══════════════════════════════════════════
#  DELIVERY
# ═══════════════════════════════════════════

@app.get("/api/v1/delivery/time")
async def api_delivery_time(lat: float, lon: float):
    minutes = calc_delivery_time(lat, lon)
    return {"status": "ok", "minutes": minutes}


@app.get("/api/v1/delivery/conditions")
async def api_delivery_conditions(delivery_type: str = "delivery"):
    conditions = get_delivery_conditions(delivery_type)
    return {"status": "ok", "conditions": conditions}


@app.get("/api/v1/delivery/slots")
async def api_delivery_slots(
    delivery_type: str = "delivery",
    wait_minutes: int = 90,
):
    slots = get_available_slots(
        delivery_type=delivery_type,
        wait_minutes=wait_minutes,
    )
    return {"status": "ok", **slots}


# ═══════════════════════════════════════════
#  WHEEL OF FORTUNE
# ═══════════════════════════════════════════

import random
from app.database import (
    seed_wheel_prizes, get_active_prizes, can_spin, save_spin,
    seed_promocodes, find_promocode,
)


@app.get("/api/v1/wheel/status")
async def api_wheel_status(user_id: int = Depends(get_current_user)):
    prizes = await get_active_prizes()
    can = await can_spin(user_id)
    return {"status": "ok", "can_spin": can, "prizes_count": len(prizes)}


@app.post("/api/v1/wheel/spin")
async def api_wheel_spin(user_id: int = Depends(get_current_user)):
    if not await can_spin(user_id):
        raise HTTPException(429, "Сегодня уже крутили — приходите завтра")
    prizes = await get_active_prizes()
    if not prizes:
        raise HTTPException(500, "Призы не настроены")
    weights = [p["weight"] for p in prizes]
    prize = random.choices(prizes, weights=weights, k=1)[0]
    prize_index = next((i for i, p in enumerate(prizes) if p["id"] == prize["id"]), 0)
    sector_angle = 360 / len(prizes)
    target_angle = 360 * 5 + (360 - prize_index * sector_angle - sector_angle / 2)
    target_angle += random.uniform(-sector_angle / 4, sector_angle / 4)
    await save_spin(user_id, prize["id"], prize["name"])
    return {
        "status": "ok",
        "prize_id": prize["id"],
        "prize_name": prize["name"],
        "angle": round(target_angle, 2),
        "spins_total": len(prizes),
        "prize_index": prize_index,
    }


# ═══════════════════════════════════════════
#  PROMOCODES
# ═══════════════════════════════════════════

class PromoApply(BaseModel):
    code: str
    cart_total: float = 0


@app.post("/api/v1/promocodes/apply")
async def api_promo_apply(
    data: PromoApply,
    user_id: int = Depends(get_current_user),
):
    promo = await find_promocode(data.code.strip())
    if not promo:
        raise HTTPException(404, "Промокод не найден")
    if data.cart_total < promo["min_order"]:
        raise HTTPException(400, f"Промокод действует от суммы {promo['min_order']} ₽")
    if promo["percent"] > 0:
        discount = round(data.cart_total * promo["percent"] / 100)
    else:
        discount = promo["discount"]
    return {
        "status": "ok",
        "code": promo["code"],
        "discount": discount,
        "description": promo["description"],
    }


# ═══════════════════════════════════════════
#  PAYMENT TYPE
# ═══════════════════════════════════════════

class PaymentSet(BaseModel):
    payment_type: str


@app.post("/api/v1/payment/set")
async def api_payment_set(
    data: PaymentSet,
    user_id: int = Depends(get_current_user),
):
    await set_payment_type(user_id, data.payment_type)
    return {"status": "ok", "payment_type": data.payment_type}


@app.get("/api/v1/payment/get")
async def api_payment_get(user_id: int = Depends(get_current_user)):
    ptype = await get_payment_type(user_id)
    return {"status": "ok", "payment_type": ptype}


# ═══════════════════════════════════════════
#  ORDER TIME
# ═══════════════════════════════════════════

class OrderTimeSet(BaseModel):
    order_time: str


@app.post("/api/v1/order-time/set")
async def api_order_time_set(
    data: OrderTimeSet,
    user_id: int = Depends(get_current_user),
):
    await set_order_time(user_id, data.order_time)
    return {"status": "ok", "order_time": data.order_time}


@app.get("/api/v1/order-time/get")
async def api_order_time_get(user_id: int = Depends(get_current_user)):
    ot = await get_order_time(user_id)
    return {"status": "ok", "order_time": ot}


# ═══════════════════════════════════════════
#  ORDER STATUS / HISTORY / REORDER
# ═══════════════════════════════════════════

@app.get("/api/v1/order/status")
async def api_order_status(
    order_id: str,
    user_id: int = Depends(get_current_user),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT order_id, total, status, created_at, items, address, phone, comment "
            "FROM orders WHERE order_id = $1 AND user_id = $2",
            order_id, user_id,
        )
    if not row:
        raise HTTPException(404, "Order not found")
    return {
        "status": "ok",
        "order": {
            "order_id": row["order_id"],
            "total": float(row["total"]),
            "status": row["status"],
            "created_at": row["created_at"].isoformat(),
            "items": row["items"],
            "address": row["address"],
            "phone": row["phone"],
            "comment": row["comment"],
        },
    }


@app.get("/api/v1/order/history")
async def api_order_history(
    limit: int = 10,
    user_id: int = Depends(get_current_user),
):
    orders = await get_user_orders(user_id, limit)
    return {"status": "ok", "orders": orders}


@app.post("/api/v1/order/reorder")
async def api_order_reorder(
    order_id: str,
    user_id: int = Depends(get_current_user),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT items FROM orders WHERE order_id = $1 AND user_id = $2",
            order_id, user_id,
        )
    if not row:
        raise HTTPException(404, "Order not found")

    items = row["items"]
    if isinstance(items, str):
        import json
        items = json.loads(items)

    await clear_cart_sk(user_id)
    for it in items:
        pid = str(it.get("plate_id"))
        cnt = int(it.get("count", 1))
        await update_cart_item(user_id, pid, cnt)

    session = await get_session(user_id)
    return await build_cart_response(user_id, session)


# ═══════════════════════════════════════════
#  ADMIN / BROADCAST
# ═══════════════════════════════════════════

class BroadcastRequest(BaseModel):
    secret: str
    text: str
    button_text: Optional[str] = None
    button_url: Optional[str] = None
    is_promo: bool = False


@app.post("/api/admin/broadcast")
async def api_admin_broadcast(data: BroadcastRequest):
    if data.secret != settings.ADMIN_SECRET:
        raise HTTPException(403, "Forbidden")
    result = await broadcast_to_all(
        text=data.text,
        button_text=data.button_text,
        button_url=data.button_url,
        only_consented=True,
    )
    return {"status": "ok", **result}


# ═══════════════════════════════════════════
#  WEBHOOK
# ═══════════════════════════════════════════

@app.post("/webhook/max")
async def webhook_max(
    update: dict,
    x_max_signature: Optional[str] = Header(None),
):
    if settings.MAX_WEBHOOK_SECRET:
        if not x_max_signature or x_max_signature != settings.MAX_WEBHOOK_SECRET:
            raise HTTPException(403, "Invalid signature")
    result = await process_webhook(update)
    return result


# ═══════════════════════════════════════════
#  ВНУТРЕННИЙ WEBHOOK КУХНИ (для SellKit / iiko)
# ═══════════════════════════════════════════

class KitchenStatusWebhook(BaseModel):
    order_id: str
    user_id: int
    new_status: str
    eta_minutes: Optional[int] = None


@app.post("/api/v1/internal/kitchen-webhook")
async def kitchen_webhook(
    payload: KitchenStatusWebhook,
    request: Request,
):
    """Внутренний эндпоинт для SellKit/iiko."""
    token = request.headers.get("X-Internal-Token")
    if token != os.getenv("INTERNAL_SECRET_TOKEN"):
        raise HTTPException(401, "Forbidden")

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE orders SET status = $1 WHERE order_id = $2",
            payload.new_status, payload.order_id,
        )

    # Пушим в WebSocket клиента
    try:
        await notify_order_status_change(
            user_id=payload.user_id,
            order_id=payload.order_id,
            new_status=payload.new_status,
            eta_minutes=payload.eta_minutes,
        )
    except Exception as e:
        logger.warning(f"WS notify failed: {e}")

    return {"success": True}