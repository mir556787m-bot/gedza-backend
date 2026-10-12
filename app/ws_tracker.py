# app/ws_tracker.py
"""
WebSocket-менеджер для трекинга статусов заказа.

Схема:
  1. Фронт открывает wss://<host>/api/v1/ws/track-order?token=<JWT>.
  2. Бэкенд валидирует JWT, извлекает user_id.
  3. Соединение хранится в active_connections[user_id].
  4. При смене статуса заказа (в БД) — send_status_update() пушит.
  5. Фронт шлёт ping каждые 30 сек, получает pong.
"""
import asyncio
import json
import logging
from typing import Dict, Set
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from starlette.websockets import WebSocketState

from app.auth import decode_token

logger = logging.getLogger(__name__)

ws_router = APIRouter(prefix="/api/v1/ws", tags=["WebSockets"])


# ═══════════════════════════════════════════
#  МЕНЕДЖЕР ПОДКЛЮЧЕНИЙ
# ═══════════════════════════════════════════

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"[WS] user {user_id} подключён. Всего: {len(self.active_connections[user_id])}")

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            logger.info(f"[WS] user {user_id} отключён")

    async def send_status_update(self, user_id: int, message: dict):
        """Отправляет обновление всем сокетам пользователя."""
        if user_id not in self.active_connections:
            logger.debug(f"[WS] user {user_id} не в сети — пуш пропущен")
            return

        dead = set()
        for ws in self.active_connections[user_id]:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_json(message)
            except Exception as e:
                logger.warning(f"[WS] send error: {e}")
                dead.add(ws)

        for ws in dead:
            self.disconnect(ws, user_id)


manager = ConnectionManager()


# ═══════════════════════════════════════════
#  WEBSOCKET ENDPOINT
# ═══════════════════════════════════════════

@ws_router.websocket("/track-order")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    Подключение к трекеру заказов.

    Фронт: new WebSocket(`wss://host/api/v1/ws/track-order?token=${jwt}`)
    """
    # 1. Валидация JWT
    payload = decode_token(token, expected_type="access")
    if not payload:
        await websocket.close(code=4003, reason="Unauthorized")
        logger.warning("[WS] попытка подключения с невалидным токеном")
        return

    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        await websocket.close(code=4003, reason="Malformed token")
        return

    # 2. Регистрация соединения
    await manager.connect(websocket, user_id)

    try:
        # 3. Пинг-понг
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "close":
                break
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"[WS] error: {e}")
        manager.disconnect(websocket, user_id)


# ═══════════════════════════════════════════
#  ВНУТРЕННИЙ API ДЛЯ СМЕНЫ СТАТУСА
# ═══════════════════════════════════════════

async def notify_order_status_change(
    user_id: int,
    order_id: str,
    new_status: str,
    title: str = "",
    subtitle: str = "",
    eta_minutes: int = None,
):
    """
    Вызывается из cart_endpoints.py при изменении статуса заказа.
    Пушит обновление в WebSocket пользователя.
    """
    packet = {
        "event": "status_changed",
        "order_id": order_id,
        "status": new_status,
        "display_title": title or _default_title(new_status),
        "display_subtitle": subtitle or _default_subtitle(new_status),
        "eta": eta_minutes,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    await manager.send_status_update(user_id, packet)
    logger.info(f"[WS] push → user {user_id}: {new_status}")


def _default_title(status: str) -> str:
    return {
        "pending_payment": "Ожидаем оплату",
        "paid": "Заказ принят",
        "cooking": "Лепим и готовим",
        "in_transit": "Курьер в пути",
        "delivered": "Приятного аппетита!",
        "cancelled": "Заказ отменён",
    }.get(status, "Обновление статуса")


def _default_subtitle(status: str) -> str:
    return {
        "pending_payment": "Завершите оплату в приложении",
        "paid": "Кухня проверяет наличие ингредиентов",
        "cooking": "Повара уже готовят ваш заказ",
        "in_transit": "Заказ передан курьеру",
        "delivered": "Ждём вас снова!",
        "cancelled": "Деньги вернутся на карту в течение 3 дней",
    }.get(status, "")