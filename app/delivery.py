# app/delivery.py
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

# ─── Условия доставки ───
DELIVERY_MIN_ORDER = 100
DELIVERY_PRICE = 150
DELIVERY_FREE_FROM = 4000
DELIVERY_WAIT_MIN = 90

# ─── Условия самовывоза ───
PICKUP_MIN_ORDER = 0
PICKUP_WAIT_MIN = 30

# ─── Слоты предзаказа ───
SLOT_STEP_MIN = 30
SLOT_WORK_START_H = 10
SLOT_WORK_START_M = 0
SLOT_WORK_END_H = 22
SLOT_WORK_END_M = 0

# ─── Часовой пояс Уфы (UTC+5) ───
UFA_OFFSET_HOURS = 5


def get_delivery_conditions(
    delivery_type: str = "delivery",
    restaurant_id: Optional[int] = None,
) -> Dict:
    if delivery_type == "pickup":
        return {
            "delivery_type": "pickup",
            "min_order": PICKUP_MIN_ORDER,
            "delivery_price": 0,
            "free_from": None,
            "wait_minutes": PICKUP_WAIT_MIN,
            "label": f"~ {PICKUP_WAIT_MIN} мин",
        }

    return {
        "delivery_type": "delivery",
        "min_order": DELIVERY_MIN_ORDER,
        "delivery_price": DELIVERY_PRICE,
        "free_from": DELIVERY_FREE_FROM,
        "wait_minutes": DELIVERY_WAIT_MIN,
        "label": f"~ {DELIVERY_WAIT_MIN} мин",
    }


def _ufa_now() -> datetime:
    """Текущее время в Уфе (UTC+5) как naive datetime."""
    return datetime.utcnow() + timedelta(hours=UFA_OFFSET_HOURS)


def _round_up_to_step(dt: datetime, step_min: int = 30) -> datetime:
    """Округляет datetime вверх до ближайшего шага."""
    minute = dt.minute
    if minute % step_min != 0:
        add = step_min - (minute % step_min)
        dt = dt + timedelta(minutes=add)
    return dt.replace(second=0, microsecond=0)


def _generate_day_slots(from_dt: datetime, to_dt: datetime) -> List[Dict]:
    """Генерирует слоты между from_dt и to_dt с шагом SLOT_STEP_MIN."""
    slots = []
    t = from_dt
    while t <= to_dt:
        slots.append({"time": t.strftime("%H:%M"), "disabled": False})
        t = t + timedelta(minutes=SLOT_STEP_MIN)
    return slots


def _day_open(d: datetime) -> datetime:
    return d.replace(
        hour=SLOT_WORK_START_H, minute=SLOT_WORK_START_M,
        second=0, microsecond=0,
    )


def _day_close(d: datetime) -> datetime:
    return d.replace(
        hour=SLOT_WORK_END_H, minute=SLOT_WORK_END_M,
        second=0, microsecond=0,
    )


def get_available_slots(
    delivery_type: str = "delivery",
    wait_minutes: int = 90,
    now: Optional[datetime] = None,
) -> Dict:
    if now is None:
        now = _ufa_now()

    # ─── 5 дней ───
    days = []
    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    for i in range(5):
        d = (now + timedelta(days=i)).date()
        if i == 0:
            label = "Сегодня"
        elif i == 1:
            label = "Завтра"
        else:
            label = f"{weekdays[d.weekday()]} {d.day}"
        days.append({
            "date": d.isoformat(),
            "label": label,
            "is_today": i == 0,
        })

    today_open = _day_open(now)
    today_close = _day_close(now)

    earliest = _round_up_to_step(
        now + timedelta(minutes=wait_minutes),
        SLOT_STEP_MIN,
    )

    slots: List[Dict] = []
    selected_day = days[0]["date"]

    if today_open <= earliest <= today_close:
        # Слоты на СЕГОДНЯ: earliest → 22:00
        slots = _generate_day_slots(earliest, today_close)

    elif earliest < today_open:
        # Раннее утро — слоты на СЕГОДНЯ с 10:00
        slots = _generate_day_slots(today_open, today_close)

    else:
        # earliest > 22:00 — слоты на ЗАВТРА
        tomorrow = now + timedelta(days=1)
        slots = _generate_day_slots(_day_open(tomorrow), _day_close(tomorrow))
        selected_day = days[1]["date"]

    return {
        "days": days,
        "slots": slots,
        "earliest": slots[0]["time"] if slots else None,
        "selected_day": selected_day,
    }