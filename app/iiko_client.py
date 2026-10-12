# app/iiko_client.py
"""
Клиент для iiko Cloud API.
Пока IIKO_ENABLED=false — все функции возвращают пустые значения.
Когда появится доступ к iiko Cloud API — здесь будет реальная интеграция.
"""
import logging
import os
from typing import Set, List

logger = logging.getLogger(__name__)

IIKO_ENABLED = os.getenv("IIKO_ENABLED", "false").lower() == "true"
IIKO_API_LOGIN = os.getenv("IIKO_API_LOGIN", "")
IIKO_ORG_ID = os.getenv("IIKO_ORG_ID", "")
IIKO_TERMINAL_GROUP_ID = os.getenv("IIKO_TERMINAL_GROUP_ID", "")
IIKO_SOURCE_KEY = os.getenv("IIKO_SOURCE_KEY", "max_bot")


async def fetch_menu_from_iiko() -> List[dict]:
    """
    Заглушка. Реализация — когда будет доступ к iiko Cloud API.
    Ожидаемый формат результата:
    [
        {
            "id": str,
            "name": str,
            "price": float,
            "old_price": float | None,
            "weight": str | None,
            "category": str,
            "badge": str | None,
            "description": str | None,
            "image": str | None,
        },
        ...
    ]
    """
    if not IIKO_ENABLED:
        return []
    logger.warning("iiko_client.fetch_menu_from_iiko: заглушка, реальный вызов не реализован")
    return []


async def fetch_stop_list() -> Set[str]:
    """
    Заглушка. Реализация — когда будет доступ к iiko Cloud API.
    Возвращает множество ID блюд, которых нет в наличии.
    """
    if not IIKO_ENABLED:
        return set()
    logger.warning("iiko_client.fetch_stop_list: заглушка, реальный вызов не реализован")
    return set()


async def create_order_in_iiko(order_data: dict) -> str | None:
    """
    Заглушка. Реализация — когда будет доступ к iiko Cloud API.
    Возвращает order_id от iiko, либо None при ошибке.
    """
    if not IIKO_ENABLED:
        return None
    logger.warning("iiko_client.create_order_in_iiko: заглушка, реальный вызов не реализован")
    return None