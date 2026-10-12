# app/restaurants.py
import logging
import math
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Рестораны Gedza в Уфе (из ТЗ)
RESTAURANTS = [
    {
        "id": 1,
        "slug": "zhukova",
        "name": "ЖУКОВА 29Ж",
        "address": "Республика Башкортостан, Уфа, улица Маршала Жукова, 29",
        "phone": "+7 (347) 200-30-04",
        "schedule": "Понедельник-Воскресенье 10:00-22:30",
        "lat": 54.7712,
        "lon": 56.0231,
        "delivery_minutes": 30,
    },
    {
        "id": 2,
        "slug": "ulyanovyh",
        "name": "УЛЬЯНОВЫХ 31",
        "address": "Республика Башкортостан, Уфа, улица Ульяновых, 31",
        "phone": "+7 (347) 200-30-05",
        "schedule": "Понедельник-Воскресенье 10:00-22:30",
        "lat": 54.7431,
        "lon": 55.9743,
        "delivery_minutes": 30,
    },
    {
        "id": 3,
        "slug": "oktyabrya",
        "name": "ПРОСПЕКТ ОКТЯБРЯ 49",
        "address": "Республика Башкортостан, Уфа, проспект Октября, 49",
        "phone": "+7 (347) 200-30-06",
        "schedule": "Понедельник-Воскресенье 10:00-22:30",
        "lat": 54.7581,
        "lon": 55.9989,
        "delivery_minutes": 30,
    },
    {
        "id": 4,
        "slug": "perovskoy",
        "name": "С.ПЕРОВСКОЙ 42",
        "address": "Республика Башкортостан, Уфа, улица Софьи Перовской, 42",
        "phone": "+7 (347) 200-30-07",
        "schedule": "Понедельник-Воскресенье 10:00-22:30",
        "lat": 54.7389,
        "lon": 55.9504,
        "delivery_minutes": 45,   # ← С.ПЕРОВСКОЙ 42 — 45 минут
    },
]


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Расстояние между двумя точками в км по формуле гаверсинусов."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_restaurants_with_distance(
    user_lat: Optional[float] = None,
    user_lon: Optional[float] = None,
) -> List[Dict]:
    """
    Возвращает список ресторанов.
    Если переданы координаты — считает дистанцию и сортирует от ближайшего.
    """
    result = []
    for r in RESTAURANTS:
        item = dict(r)
        if user_lat is not None and user_lon is not None:
            item["distance_km"] = round(
                haversine(user_lat, user_lon, r["lat"], r["lon"]), 1
            )
        else:
            item["distance_km"] = None
        result.append(item)

    if user_lat is not None and user_lon is not None:
        result.sort(key=lambda x: x["distance_km"])

    return result


def get_restaurant_by_id(restaurant_id: int) -> Optional[Dict]:
    for r in RESTAURANTS:
        if r["id"] == restaurant_id:
            return dict(r)
    return None


def calc_delivery_time(user_lat: float, user_lon: float) -> int:
    """
    Расчёт времени доставки в минутах.
    Простая формула: 30 мин фикс + 2 мин на км до ближайшего ресторана.
    """
    nearest = get_restaurants_with_distance(user_lat, user_lon)[0]
    distance = nearest.get("distance_km", 5.0)
    return int(30 + distance * 2)