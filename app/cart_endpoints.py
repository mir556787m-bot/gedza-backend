# app/cart_endpoints.py
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.cart_manager import (
    build_cart_response, update_cart_item, clear_cart,
    set_comment, set_payment_type, set_order_datetime,
    update_addition, get_cart_raw, get_payment_type,
    get_order_datetime, get_comment, add_promocode, delete_promocode,
)
from app.database import get_session, find_promocode, get_pool
from app.max_bot import send_order_notification
from app.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/cart", tags=["cart"])

@router.get("/get")
async def cart_get(user_id: int = Depends(get_current_user)):
    session = await get_session(user_id)
    return await build_cart_response(user_id, session)

@router.post("/change")
async def cart_change(plate_id: str, count: int, user_id: int = Depends(get_current_user)):
    current = int((await get_cart_raw(user_id)).get(str(plate_id), 0))
    delta = count - current
    await update_cart_item(user_id, plate_id, delta)
    session = await get_session(user_id)
    return await build_cart_response(user_id, session)

@router.post("/remove")
async def cart_remove(plate_id: str, user_id: int = Depends(get_current_user)):
    await update_cart_item(user_id, plate_id, -99999)
    session = await get_session(user_id)
    return await build_cart_response(user_id, session)

@router.post("/clear")
async def cart_clear(user_id: int = Depends(get_current_user)):
    await clear_cart(user_id)
    return {"error": False}

@router.post("/comment")
async def cart_comment(comment: str, user_id: int = Depends(get_current_user)):
    if len(comment) > 500:
        raise HTTPException(400, "Комментарий слишком длинный")
    await set_comment(user_id, comment)
    return {"error": False}

@router.post("/payment")
async def cart_payment(payment_type: str, user_id: int = Depends(get_current_user)):
    allowed = {"15", "16", "17", "cash", "card_on_delivery", "card_online"}
    if payment_type not in allowed:
        raise HTTPException(400, "Недопустимый способ оплаты")
    await set_payment_type(user_id, payment_type)
    return {"error": False}

@router.post("/datetime")
async def cart_datetime(order_datetime: str, user_id: int = Depends(get_current_user)):
    if len(order_datetime) > 100:
        raise HTTPException(400, "Некорректное значение времени")
    await set_order_datetime(user_id, order_datetime)
    return {"error": False}

@router.post("/promo/add")
async def cart_promo_add(code: str, user_id: int = Depends(get_current_user)):
    if not code or len(code) > 50:
        raise HTTPException(400, "Некорректный промокод")
    return await add_promocode(user_id, code)

@router.post("/promo/delete")
async def cart_promo_delete(user_id: int = Depends(get_current_user)):
    await delete_promocode(user_id)
    return {"error": False}

@router.post("/addition")
async def cart_addition(addition_id: str, delta: int, user_id: int = Depends(get_current_user)):
    if delta < -99 or delta > 99:
        raise HTTPException(400, "Некорректное количество")
    await update_addition(user_id, addition_id, delta)
    session = await get_session(user_id)
    return await build_cart_response(user_id, session)

@router.post("/phone")
async def cart_phone(phone: str, user_id: int = Depends(get_current_user)):
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 11:
        raise HTTPException(400, "Некорректный номер телефона")
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET phone = $1, updated_at = NOW() WHERE user_id = $2", phone, user_id)
    return {"error": False, "phone": phone}

@router.get("/stoplist")
async def cart_stoplist(user_id: int = Depends(get_current_user)):
    from app.cache import get_stop_list_cache
    stop_ids = await get_stop_list_cache()
    if not stop_ids:
        return {"stoplist": []}
    cart = await get_cart_raw(user_id)
    in_stop = [pid for pid in cart.keys() if str(pid) in stop_ids]
    return {"stoplist": in_stop}

class CreateOrderRequest(BaseModel):
    phone: str
    marketing_consent: bool = True
    address: Optional[str] = None

@router.post("/create-order")
async def cart_create_order(data: CreateOrderRequest, user_id: int = Depends(get_current_user)):
    digits = "".join(c for c in data.phone if c.isdigit())
    if len(digits) < 11:
        raise HTTPException(400, "Некорректный номер телефона")

    cart = await get_cart_raw(user_id)
    if not cart:
        raise HTTPException(400, "Корзина пуста")

    from app.cache import get_menu_cache
    menu = await get_menu_cache() or []
    menu_map = {str(m.get("plateID")): m for m in menu}

    total = 0.0
    order_items = []
    for plate_id, count in cart.items():
        item = menu_map.get(str(plate_id))
        if not item:
            continue
        price = float(item.get("price", 0))
        total += price * count
        order_items.append({"plate_id": plate_id, "name": item.get("plateName", item.get("name", "")), "price": price, "count": count, "sum": price * count})

    if not order_items:
        raise HTTPException(400, "Все товары недоступны")

    session = await get_session(user_id)
    delivery_type = "delivery"
    delivery_address = data.address or ""
    if session:
        delivery_type = session.get("delivery_type", "delivery")
        if not delivery_address:
            delivery_address = session.get("address", "")

    final_total = int(total)
    import uuid, json
    order_id = f"GDZ-{datetime.now().strftime(chr(37)+chr(121)+chr(37)+chr(109)+chr(37)+chr(100))}-{uuid.uuid4().hex[:6].upper()}"

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO orders (order_id, user_id, total, items, address, phone, comment, status) VALUES ($1, $2, $3, $4, $5, $6, $7, chr(39)||chr(110)||chr(101)||chr(119)||chr(39))", order_id, user_id, final_total, json.dumps(order_items, ensure_ascii=False), delivery_address, data.phone, "")

    await clear_cart(user_id)
    try:
        await send_order_notification(user_id, order_id, final_total)
    except Exception:
        pass
    return {"status": "ok", "order_id": order_id, "total": final_total}

from app.cart_commands import (
    toggle_promo,
    set_promos,
    clear_promos,
    get_promos_ids,
    get_active_promos,
)

@router.post("/command/toggle-promo")
async def cart_command_toggle_promo(promo_id: int, user_id: int = Depends(get_current_user)):
    result = await toggle_promo(user_id, promo_id)
    session = await get_session(user_id)
    cart = await build_cart_response(user_id, session)
    return {**result, "cart": cart}

@router.post("/command/clear-promos")
async def cart_command_clear_promos(user_id: int = Depends(get_current_user)):
    result = await clear_promos(user_id)
    session = await get_session(user_id)
    cart = await build_cart_response(user_id, session)
    return {**result, "cart": cart}

class SetPromosCommand(BaseModel):
    promosIdsString: str = ""

@router.post("/command/set-promos")
async def cart_command_set_promos(data: SetPromosCommand, user_id: int = Depends(get_current_user)):
    result = await set_promos(user_id, data.promosIdsString)
    session = await get_session(user_id)
    cart = await build_cart_response(user_id, session)
    return {**result, "cart": cart}
