# app/sellkit_provider.py
"""
Провайдер меню из SellKit API.
Возвращает меню в формате, совместимом с парсером.
Пока SELLKIT_AUTH_TOKEN пуст — функция возвращает [].

Использование:
1. Заполнить в .env:
   SELLKIT_AUTH_TOKEN=<токен из F12 DevTools>
   SELLKIT_DEVICE_ID=<device-id из F12>
   SELLKIT_ORG_ID=2
   MENU_SOURCE=sellkit
2. Перезапустить backend.
3. Меню будет забираться из API, а не парситься.
"""
import logging
import os
import httpx

logger = logging.getLogger(__name__)


# ─── Настройки из ENV ───
SELLKIT_API_URL = os.getenv("SELLKIT_API_URL", "https://all.s2.sellkit.ru/NewApi")
SELLKIT_AUTH_TOKEN = os.getenv("SELLKIT_AUTH_TOKEN", "")
SELLKIT_DEVICE_ID = os.getenv("SELLKIT_DEVICE_ID", "")
SELLKIT_ORG_ID = os.getenv("SELLKIT_ORG_ID", "2")


async def fetch_menu_from_sellkit() -> list:
    """
    Забирает меню из SellKit API (Content/GetCatalog.php).
    Возвращает список блюд в формате, который отдаёт наш парсер.
    """
    if not SELLKIT_AUTH_TOKEN:
        logger.info("SELLKIT_AUTH_TOKEN пуст — SellKit API отключён")
        return []

    headers = {
        "authorization": SELLKIT_AUTH_TOKEN,
        "device-id": SELLKIT_DEVICE_ID or SELLKIT_AUTH_TOKEN,
        "accept": "application/json, text/plain, */*",
        "origin": "https://gedzagroup.ru",
        "referer": "https://gedzagroup.ru/",
    }

    try:
        async with httpx.AsyncClient(timeout=30, verify=False) as client:
            r = await client.post(
                f"{SELLKIT_API_URL}/Content/GetCatalog.php",
                headers=headers,
                data={
                    "OrganisationID": SELLKIT_ORG_ID,
                    "cityId": "0",
                    "web": "true",
                },
            )
            if r.status_code != 200:
                logger.warning(f"SellKit API вернул {r.status_code}: {r.text[:200]}")
                return []
            data = r.json()
    except Exception as e:
        logger.error(f"SellKit API ошибка: {e}")
        return []

    # ─── Трансляция ответа SellKit в наш формат ───
    items = []

    # Структура SellKit: data['Catalog'] → список категорий
    # Каждая категория: {'Name': 'Комбо', 'Plates': [{'PlateID': 415, 'Name': '...', ...}]}
    catalog = data.get("Catalog") or data.get("categories") or []
    if isinstance(catalog, dict):
        catalog = list(catalog.values())

    for category in catalog:
        if not isinstance(category, dict):
            continue
        cat_name = category.get("Name") or category.get("name") or ""
        plates = category.get("Plates") or category.get("plates") or []

        for plate in plates:
            if not isinstance(plate, dict):
                continue

            plate_id = str(plate.get("PlateID") or plate.get("plateID") or "")
            name = plate.get("Name") or plate.get("name") or ""
            price_raw = plate.get("Price") or plate.get("price") or 0
            mass = plate.get("Mass") or plate.get("mass") or ""
            picture = plate.get("Picture") or plate.get("picture") or plate.get("ThumbnailPicture") or ""
            description = plate.get("Description") or plate.get("description") or ""
            sku = str(plate.get("sku") or plate.get("SKU") or plate_id)

            try:
                price = int(float(price_raw))
            except Exception:
                price = 0

            if not name or price <= 0:
                continue

            # slug-id из имени (для совместимости с карточками)
            from app.parser import _slugify
            slug = _slugify(name)

            items.append({
                # Внутренние поля (для фронта карточек)
                "id": slug,
                "name": name,
                "description": description,
                "price": price,
                "old_price": None,
                "weight": mass or None,
                "category": cat_name,
                "badge": None,
                "image": picture,

                # SellKit-поля (для корзины)
                "plateID": plate_id,
                "plateName": name,
                "cleanPrice": str(price),
                "thumbnailPicture": picture,
                "mass": mass,
                "categoryName": cat_name,
                "sku": sku,
            })

    logger.info(f"SellKit API: получено {len(items)} позиций")
    return items