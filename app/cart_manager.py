# app/cart_manager.py
"""
Менеджер корзины. Формат SellKit.

⚡ Особенности:
  - Автопромокоды фильтруются по типу доставки и по категориям.
  - Явные промокоды хранятся как строка ID ("53,54").
  - Промокоды с category_name применяются только при наличии товара из категории.
  - Защита от двойной скидки: автопромокод исключается из явных.
  - Скрытые промокоды (is_hidden=TRUE) не показываются.
  - Для самовывоза addressSubtitle = полный адрес точки.
  - Стоп-лист: недоступные товары помечаются cannotOrderNow=True.
  - Скидка округляется по математическим правилам (round).
  - Скидка начисляется только на товары, без допов и доставки.
  - Склонение «товар/товара/товаров».
  - Порядок строк чека: баллы → товары → дополнения → скидка → доставка.
  - Автопромокоды учитываются в selected (фронт показывает галочку).
  - ⚡ Для овальной кнопки «применённого промокода» используется tag
    (короткое имя, например «Самовывоз»), а не длинный title.
"""
import logging
import json
from typing import Dict, List, Optional, Any

from app.cache import get_redis, get_menu_cache, get_stop_list_cache
from app.database import get_user_profile, find_promocode, get_pool

logger = logging.getLogger(__name__)

BONUS_PERCENT = 0.03
FREE_DELIVERY_THRESHOLD = 4000
DELIVERY_PRICE = 150


# ═══════════════════════════════════════════
#  УТИЛИТЫ
# ═══════════════════════════════════════════

def _plural_ru(n: int, one: str, few: str, many: str) -> str:
    """Склонение русских существительных: 1 товар, 2 товара, 5 товаров."""
    mod10 = n % 10
    mod100 = n % 100
    if mod10 == 1 and mod100 != 11:
        return one
    if 2 <= mod10 <= 4 and not (12 <= mod100 <= 14):
        return few
    return many


# ═══════════════════════════════════════════
#  ОСНОВНЫЕ ОПЕРАЦИИ
# ═══════════════════════════════════════════

async def get_cart_raw(user_id: int) -> Dict[str, int]:
    r = await get_redis()
    data = await r.hgetall(f"cart:{user_id}")
    return {k: int(v) for k, v in data.items()}


async def update_cart_item(user_id: int, plate_id: str, delta: int) -> Dict[str, int]:
    r = await get_redis()
    key = f"cart:{user_id}"
    current = int(await r.hget(key, plate_id) or 0)
    new_count = current + delta
    if new_count <= 0:
        await r.hdel(key, plate_id)
    else:
        await r.hset(key, plate_id, new_count)
    await r.expire(key, 86400 * 7)
    return await get_cart_raw(user_id)


async def clear_cart(user_id: int):
    r = await get_redis()
    await r.delete(
        f"cart:{user_id}",
        f"cart:comment:{user_id}",
        f"cart:payment:{user_id}",
        f"cart:datetime:{user_id}",
        f"cart:promo:{user_id}",
        f"cart:promos:{user_id}",
        f"cart:additions:{user_id}",
    )


async def set_comment(user_id: int, comment: str):
    r = await get_redis()
    await r.set(f"cart:comment:{user_id}", comment, ex=86400 * 7)


async def get_comment(user_id: int) -> str:
    r = await get_redis()
    return await r.get(f"cart:comment:{user_id}") or ""


async def set_payment_type(user_id: int, payment_type: str):
    r = await get_redis()
    await r.set(f"cart:payment:{user_id}", payment_type, ex=86400 * 7)


async def get_payment_type(user_id: int) -> str:
    """Дефолт — '16' = Картой при получении (SellKit paymentType)."""
    r = await get_redis()
    return await r.get(f"cart:payment:{user_id}") or "16"


async def set_order_datetime(user_id: int, order_datetime: str):
    r = await get_redis()
    await r.set(f"cart:datetime:{user_id}", order_datetime, ex=86400 * 7)


async def get_order_datetime(user_id: int) -> str:
    r = await get_redis()
    return await r.get(f"cart:datetime:{user_id}") or "now"


async def add_promocode(user_id: int, code: str) -> Dict[str, Any]:
    from app.cart_commands import toggle_promo
    code = (code or "").strip()
    if not code:
        return {"isHave": False, "message": "Промокод пустой"}

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, code FROM promocodes "
            "WHERE UPPER(code) = UPPER($1) AND is_active = TRUE",
            code,
        )
    if not row:
        return {"isHave": False, "message": "Промокод не найден"}

    result = await toggle_promo(user_id, row["id"])
    return {
        "isHave": True,
        "message": "Промокод применён",
        "code": row["code"],
        "promosIdsString": result.get("promosIdsString", ""),
    }


async def delete_promocode(user_id: int):
    from app.cart_commands import clear_promos
    await clear_promos(user_id)


async def get_promocode(user_id: int) -> Optional[str]:
    from app.cart_commands import get_promos_ids
    return await get_promos_ids(user_id) or None


async def update_addition(user_id: int, addition_id: str, delta: int):
    r = await get_redis()
    key = f"cart:additions:{user_id}"
    current = int(await r.hget(key, addition_id) or 0)
    new_count = current + delta
    if new_count <= 0:
        await r.hdel(key, addition_id)
    else:
        await r.hset(key, addition_id, new_count)
    await r.expire(key, 86400 * 7)


async def get_additions(user_id: int) -> Dict[str, int]:
    r = await get_redis()
    data = await r.hgetall(f"cart:additions:{user_id}")
    return {k: int(v) for k, v in data.items()}


# ═══════════════════════════════════════════
#  ЛОГИКА ПРОМОКОДОВ
# ═══════════════════════════════════════════

def _promo_matches_category(promo: dict, cart_categories: set) -> bool:
    cat = promo.get("category_name")
    if not cat:
        return True
    return cat in cart_categories


def _promo_matches_delivery(promo: dict, delivery_type: str) -> bool:
    dt = str(promo.get("delivery_types") or "")
    if not dt:
        return True
    return str(delivery_type) in dt.replace(" ", "").split(",")


async def _apply_auto_promos(cart_items: List[dict], delivery_type: str) -> List[dict]:
    """Автопромокоды (auto_activate=TRUE), исключая скрытые (is_hidden=TRUE)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, code, title, description, tag, percent, discount, "
            "       sale_type, promocode_type, delivery_types, min_cart_price, "
            "       gift_name, gift_picture, category_name, applies_to_category_only "
            "FROM promocodes "
            "WHERE is_active = TRUE AND auto_activate = TRUE AND is_hidden = FALSE"
        )

    cart_categories = {item.get("categoryName", "") for item in cart_items}
    cart_total = sum(
        float(i.get("price", 0)) * int(i.get("count", 0))
        for i in cart_items
    )

    applied = []
    for r in rows:
        promo = dict(r)
        if not _promo_matches_delivery(promo, delivery_type):
            continue
        if promo["min_cart_price"] and cart_total < promo["min_cart_price"]:
            continue
        if not _promo_matches_category(promo, cart_categories):
            continue

        applied.append({
            "id": str(promo["id"]),
            "code": promo["code"],
            "title": promo["title"] or promo["code"],
            "description": promo["description"] or "",
            "tag": promo["tag"] or "",
            "promocodeType": promo["promocode_type"],
            "saleType": promo["sale_type"],
            "percent": promo["percent"] or 0,
            "discount": promo["discount"] or 0,
            "gift_name": promo["gift_name"],
            "gift_picture": promo["gift_picture"],
            "category_name": promo["category_name"],
            "applies_to_category_only": bool(promo["applies_to_category_only"]),
        })
    return applied


async def _get_available_promos(
    delivery_type: str,
    menu_categories: set,
    active_promo_ids: set,
    auto_promo_ids: Optional[set] = None,
) -> List[dict]:
    """
    Доступные промокоды для UI. Скрытые — не показываются.

    ⚡ selected = TRUE, если промокод:
       - явно выбран пользователем (active_promo_ids), ИЛИ
       - автоматически активен (auto_promo_ids, например «Самовывоз» при pickup)
    """
    auto_promo_ids = auto_promo_ids or set()

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, code, title, description, tag, percent, discount, "
            "       sale_type, promocode_type, delivery_types, category_name "
            "FROM promocodes "
            "WHERE is_active = TRUE AND is_hidden = FALSE ORDER BY id"
        )

    promos = []
    for r in rows:
        promo = dict(r)
        if not _promo_matches_delivery(promo, delivery_type):
            continue
        cat = promo.get("category_name")
        if cat and cat not in menu_categories:
            continue

        pid = str(promo["id"])
        promos.append({
            "id": pid,
            "promocode": promo["code"],
            "title": promo["title"] or promo["code"],
            "description": promo["description"] or "",
            "tag": promo["tag"] or "Промокод",
            "selected": pid in active_promo_ids or pid in auto_promo_ids,
        })
    return promos


def _calculate_discount_from_promos(
    total: float,
    promos: List[dict],
    cart_items: List[dict],
) -> int:
    """Считает скидку с математическим округлением. Только на товары (без допов и доставки)."""
    discount = 0
    for p in promos:
        base_total = total
        if p.get("applies_to_category_only") and p.get("category_name"):
            cat = p["category_name"]
            base_total = sum(
                float(i.get("price", 0)) * int(i.get("count", 0))
                for i in cart_items
                if i.get("categoryName") == cat
            )
        if p.get("percent"):
            discount += round(base_total * p["percent"] / 100)
        elif p.get("discount"):
            discount += p["discount"]
    return discount


# ═══════════════════════════════════════════
#  ФОРМИРОВАНИЕ ОТВЕТА SellKit
# ═══════════════════════════════════════════

async def build_cart_response(user_id: int, session: Optional[dict] = None) -> dict:
    from app.cart_commands import get_promos_ids, get_active_promos

    cart_raw = await get_cart_raw(user_id)
    additions_raw = await get_additions(user_id)
    comment = await get_comment(user_id)
    payment_type = await get_payment_type(user_id)
    order_datetime = await get_order_datetime(user_id)

    promos_ids_str = await get_promos_ids(user_id)
    active_promos = await get_active_promos(user_id)
    active_promo_ids = set(promos_ids_str.split(",")) if promos_ids_str else set()

    menu = await get_menu_cache() or []
    menu_categories = {m.get("categoryName", m.get("category", "")) for m in menu}

    stop_ids = await get_stop_list_cache()

    # ─── Тип доставки + адрес ───
    delivery_type = "2"
    address_title = "Выберите адрес"
    address_full = ""
    address_subtitle = "Не выбрано"
    delivery_minutes = 90
    restaurant_id = None

    if session:
        delivery_type = "1" if session.get("delivery_type") == "pickup" else "2"

        if session.get("delivery_type") == "pickup":
            addr_details = session.get("address_details") or {}
            if isinstance(addr_details, str):
                try:
                    addr_details = json.loads(addr_details)
                except Exception:
                    addr_details = {}

            restaurant_id = addr_details.get("restaurant_id")
            r_obj = None
            if restaurant_id:
                try:
                    from app.restaurants import get_restaurant_by_id
                    r_obj = get_restaurant_by_id(int(restaurant_id))
                except Exception as e:
                    logger.warning(f"restaurant lookup failed: {e}")

            if r_obj:
                address_title = r_obj.get("name", "Точка самовывоза")
                address_full = r_obj.get("address", "")
                delivery_minutes = r_obj.get("delivery_minutes", 30)
            else:
                address_title = session.get("address", "Точка самовывоза")
                address_full = addr_details.get("restaurant_address", "")

            address_subtitle = address_full or address_title
        else:
            address_title = session.get("address", "") or "Выберите адрес"
            address_full = session.get("address", "")
            address_subtitle = "Доставка"

    # ─── Товары ───
    plates = []
    total = 0.0
    for plate_id, count in cart_raw.items():
        item = next((m for m in menu if str(m.get("plateID")) == str(plate_id)), None)
        if not item:
            continue
        price = float(item.get("price", 0))
        total += price * count
        is_stopped = str(plate_id) in stop_ids
        plates.append({
            "id": item.get("id"),
            "plateID": item.get("plateID"),
            "count": count,
            "price": str(int(price)),
            "modifiers": "",
            "modifiersIds": '{"data":[]}',
            "mass": item.get("mass", "") or item.get("weight", "") or "",
            "comment": "",
            "isFromRecomendations": "0",
            "cannotOrderNow": is_stopped,
            "needToDelete": is_stopped,
            "timeTags": [],
            "categoryID": "",
            "subCategoryID": "0",
            "sku": item.get("sku", item.get("plateID")),
            "categoryName": item.get("categoryName", item.get("category", "")),
            "cleanPrice": item.get("cleanPrice", str(int(price))),
            "modifiersPrice": "0",
            "maxCount": 99,
            "canHaveSale": "1",
            "plateName": item.get("plateName", item.get("name", "")),
            "isForBonuses": "0",
            "canSumWithGifts": "1",
            "canSumWithPromos": "1",
            "canSumWithBonuses": "1",
            "thumbnailPicture": item.get("thumbnailPicture", item.get("image", "")),
            "gifts": [],
        })

    # ─── Автопромокоды ───
    auto_applied = await _apply_auto_promos(plates, delivery_type)
    auto_discount = _calculate_discount_from_promos(total, auto_applied, plates)
    auto_ids = {str(p["id"]) for p in auto_applied}

    # ─── Явные промокоды (без дублей с автопромокодами) ───
    valid_explicit = []
    cart_categories = {item.get("categoryName", "") for item in plates}
    for p in active_promos:
        if str(p["id"]) in auto_ids:
            continue
        if not _promo_matches_delivery(p, delivery_type):
            continue
        if not _promo_matches_category(p, cart_categories):
            continue
        valid_explicit.append(p)

    explicit_discount = _calculate_discount_from_promos(total, valid_explicit, plates)
    total_discount = auto_discount + explicit_discount

    # ─── Добавки ───
    additions_menu_all = [m for m in menu if m.get("categoryName") == "Дополнительно"]
    additions_menu = [
        m for m in additions_menu_all
        if "палочк" not in (m.get("plateName", m.get("name", ""))).lower()
    ]
    additions = []
    additions_price = 0.0
    for add in additions_menu[:3]:
        add_id = str(add.get("plateID"))
        cnt = additions_raw.get(add_id, 0)
        price = float(add.get("price", 0))
        additions_price += price * cnt
        additions.append({
            "id": add_id,
            "title": add.get("plateName", add.get("name", "")),
            "maxCount": 120,
            "freeCount": 0,
            "price": str(int(price)),
            "priceDescription": f"{int(price)}₽",
            "picture": add.get("thumbnailPicture", ""),
            "count": cnt,
        })

    # ─── Подарки ───
    order_gifts = []
    for p in auto_applied:
        if p["saleType"] == "gift" and p["gift_name"]:
            order_gifts.append({
                "plateID": "999",
                "plateName": p["gift_name"],
                "thumbnailPicture": p["gift_picture"] or "",
                "mass": "250 г",
                "isGift": True,
                "price": "0",
            })

    # ─── Прогресс до бесплатной доставки ───
    fill = min(1.0, total / FREE_DELIVERY_THRESHOLD) if FREE_DELIVERY_THRESHOLD else 0
    left = max(0, FREE_DELIVERY_THRESHOLD - total)

    delivery_banner = {
        "isShow": total < FREE_DELIVERY_THRESHOLD and total > 0 and delivery_type == "2",
        "title": f"еще {int(left)} ₽",
        "subtitle": "и доставка будет бесплатная",
        "fill": f"{fill:.4f}",
    }

    # ─── Способы оплаты ───
    order_payment_types = [
        {"paymentType": "15", "type": "0", "title": "Наличные", "isNeedToChangeCash": False},
        {"paymentType": "16", "type": "1", "title": "Картой при получении", "isNeedToChangeCash": False},
        {"paymentType": "17", "type": "2", "title": "Картой онлайн", "isNeedToChangeCash": False},
    ]

    # ─── Рекомендации ───
    recomendations = []
    cutlery_item = next(
        (m for m in additions_menu_all if "палочк" in (m.get("plateName", m.get("name", ""))).lower()),
        None,
    )
    if cutlery_item:
        recomendations.append({
            "isHaveInCart": str(cutlery_item.get("plateID")) in cart_raw,
            "countInCart": cart_raw.get(str(cutlery_item.get("plateID")), 0),
            "plateID": cutlery_item.get("plateID"),
            "name": cutlery_item.get("plateName", cutlery_item.get("name", "")),
            "price": str(int(cutlery_item.get("price", 0))),
            "salePrice": "0",
            "thumbnailPicture": cutlery_item.get("thumbnailPicture", ""),
            "mass": cutlery_item.get("mass", ""),
            "mass_num": "0",
            "mass_type": "",
        })

    # ⚡ Доступные промокоды — с учётом автопромокодов в selected
    available_promos = await _get_available_promos(
        delivery_type, menu_categories, active_promo_ids, auto_ids,
    )

    # ─── Все цены (чек) ───
    delivery_price = 0 if delivery_type == "1" or total >= FREE_DELIVERY_THRESHOLD else DELIVERY_PRICE

    plates_count = sum(int(p["count"]) for p in plates)
    plates_word = _plural_ru(plates_count, "товар", "товара", "товаров")

    final_total = round(total + additions_price + delivery_price - total_discount)
    bonus_earned = round(final_total * BONUS_PERCENT)

    # ⚡ Порядок строк чека по ТЗ «Блок 3»:
    #    1. Начислим баллы
    #    2. Товары
    #    3. Платные дополнения
    #    4. Скидка
    #    5. Доставка
    all_prices = []

    if bonus_earned > 0:
        all_prices.append({
            "title": "Начислим баллы",
            "value": f"+{bonus_earned}",
            "isBonuses": True,
        })

    if plates_count > 0:
        all_prices.append({
            "title": f"{plates_count} {plates_word}",
            "value": f"{int(round(total))} ₽",
            "isBonuses": False,
        })

    if additions_price > 0:
        all_prices.append({
            "title": "Платные дополнения",
            "value": f"{int(round(additions_price))} ₽",
            "isBonuses": False,
        })

    if total_discount > 0:
        all_prices.append({
            "title": "Скидка",
            "value": f"-{round(total_discount)} ₽",
            "isBonuses": False,
        })

    if delivery_price > 0:
        all_prices.append({
            "title": "Доставка",
            "value": f"{delivery_price} ₽",
            "isBonuses": False,
        })

    # ═══════════════════════════════════════════
    #  ⚡ ПРИМЕНЁННЫЕ АКЦИИ
    #  Для овальной кнопки «применённого промокода» используем tag
    #  (короткое имя, например «Самовывоз»), а не длинный title.
    # ═══════════════════════════════════════════
    applied_promos_list = []
    for p in auto_applied:
        applied_promos_list.append({
            "id": p["id"],
            "title": p.get("tag") or p.get("title") or p.get("code", ""),
        })
    for p in valid_explicit:
        applied_promos_list.append({
            "id": str(p["id"]),
            "title": p.get("tag") or p.get("title") or p.get("code", ""),
        })

    all_applied_sales = []
    for p in auto_applied:
        all_applied_sales.append({
            "id": p["id"],
            "title": p["title"],
            "sale": str(p["percent"] or p["discount"] or 0),
            "promocodeType": p["promocodeType"],
            "gifts": "",
            "iikoId": None,
        })
    for p in valid_explicit:
        all_applied_sales.append({
            "id": str(p["id"]),
            "title": p["title"] or p["code"],
            "sale": str(p["percent"] or p["discount"] or 0),
            "promocodeType": p.get("promocode_type", 0),
            "gifts": "",
            "iikoId": None,
        })

    ui_address_subtitle = (
        address_subtitle if delivery_type == "1" else (address_full or "Доставка")
    )

    # Текст описания применённого промокода (для зелёной надписи)
    promo_description = ""
    if auto_applied:
        promo_description = auto_applied[0].get("description", "")
    elif valid_explicit:
        promo_description = valid_explicit[0].get("description", "")

    return {
        "plates": plates,
        "orderGifts": order_gifts,
        "cutleryTitle": "Приборы к заказу",
        "cutlery": [],
        "cutleryPrice": 0,
        "additionsTitle": "Добавить к заказу",
        "additions": additions,
        "additionsCount": sum(additions_raw.values()),
        "paidAdditionsCount": sum(additions_raw.values()),
        "additionsPrice": int(round(additions_price)),
        "isHaveMultipleGifts": "1",
        "platesPrice": str(int(round(total))),
        "platesPriceTitle": f"{plates_count} {plates_word} на {int(round(total))} ₽",

        "lastOrderPaymentType": payment_type,
        "lastOrderPaymentTypeType": "-1",
        "lastOrderPaymentTitle": next(
            (pt["title"] for pt in order_payment_types if pt["paymentType"] == payment_type),
            "Картой при получении",
        ),
        "orderPaymentTypes": order_payment_types,

        "orderDateTime": order_datetime,
        "orderDateTimeText": "Как можно быстрее" if order_datetime == "now" else order_datetime,
        "orderDateTimeTextNew": "Когда оформить заказ",
        "canPreorder": True,
        "canOrderNow": True,

        "deliveryType": delivery_type,
        "deliveryTime": f"~ {delivery_minutes} мин",
        "deliveryMinutes": delivery_minutes,
        "restaurantId": restaurant_id,
        "addressTitleCart": f"{'Самовывоз' if delivery_type == '1' else 'Доставка'} на {address_title}",
        "addressTitle": address_title,
        "addressSubtitle": ui_address_subtitle,
        "addressFull": address_full,
        "deliveryDetails": [
            {"title": "Минимальный заказ", "subtitle": "0 ₽"},
            {"title": "Время ожидания", "subtitle": f"~ {delivery_minutes} мин"},
        ],
        "deliveryPriceBanner": delivery_banner,
        "minOrderPriceBanner": {
            "isShow": False,
            "title": "еще 0 ₽",
            "subtitle": "до минимальной суммы заказа",
            "fill": "1",
        },
        "freeDeliveryPrice": 0,

        "orderComment": comment,

        "promosIdsString": promos_ids_str,
        "usingPromocode": len(valid_explicit) > 0 or len(auto_applied) > 0,
        "canHavePromocode": True,
        "autoPromocodes": {
            "title": "Вам доступны промокоды!",
            "promocodes": available_promos,
        },
        "appliedPromos": {
            "title": "Примененные акции",
            "promos": applied_promos_list,
        },
        "allAppliedPromosSales": all_applied_sales,
        "promoDescription": promo_description,
        "promoDiscount": total_discount,

        "recomendations": recomendations,
        "recommendationsTitle": "Что-нибудь еще?",

        "isCanGetBonuses": False,
        "isCanPayByBonuses": False,
        "bonusesToPay": "0",
        "bonusesToGet": str(bonus_earned),
        "bonusEarned": bonus_earned,
        "userBonuses": "0",

        "allPrices": all_prices,
        "totalPrice": str(int(round(total))),
        "saleTotalPrice": str(final_total),

        "canOrder": len(plates) > 0 and not any(p["cannotOrderNow"] for p in plates),
        "correctMinPrice": True,
        "orderMinPrice": "0",

        "orderPopup": {
            "isHave": True,
            "title": "",
            "text": "Соевый соус, имбирь и васаби продаются отдельно",
            "restrictOrder": False,
            "buttonContinue": "Понятно",
            "buttonClose": "Вернуться",
        },
    }