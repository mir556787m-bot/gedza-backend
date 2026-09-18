# app/poller.py
"""
Long Polling для MAX Bot API.
Работает без публичного HTTPS — не требует валидного SSL.

При ошибке 401 (неверный токен) делает паузу 60 секунд,
чтобы не спамить запросами к MAX API.
"""
import asyncio
import logging
import httpx
from app.config import settings
from app.webhook import _process_update

logger = logging.getLogger(__name__)

MAX_API = settings.MAX_API_URL
_polling_task = None


async def _get_updates(marker: int | None = None) -> dict:
    """
    Получает пакет обновлений от MAX.

    При ошибке 401 — пауза 60 секунд (токен недействителен).
    При других ошибках — пауза 5 секунд.
    """
    params = {"limit": 100, "timeout": 30}
    if marker is not None:
        params["marker"] = marker

    url = f"{MAX_API}/updates"
    headers = {"Authorization": settings.MAX_BOT_TOKEN}

    try:
        async with httpx.AsyncClient(timeout=40, verify=False) as client:
            r = await client.get(url, params=params, headers=headers)

            if r.status_code == 200:
                return r.json()

            if r.status_code == 401:
                logger.error(
                    "MAX API: 401 Unauthorized — токен недействителен. "
                    "Пауза 60 секунд. Проверьте MAX_BOT_TOKEN в .env."
                )
                await asyncio.sleep(60)
                return {}

            logger.error(f"Polling error {r.status_code}: {r.text[:200]}")
            await asyncio.sleep(5)
            return {}

    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"Polling exception: {e}")
        await asyncio.sleep(5)
        return {}


async def polling_loop():
    """Бесконечный цикл опроса MAX."""
    logger.info("Long Polling запущен")
    marker = None

    while True:
        try:
            data = await _get_updates(marker)
            updates = data.get("updates", [])
            marker = data.get("marker", marker)

            if updates:
                logger.info(f"Получено {len(updates)} обновлений")
                for update in updates:
                    try:
                        await _process_update(update)
                    except Exception as e:
                        logger.error(f"Ошибка обработки обновления: {e}")
            else:
                # Нет событий — короткая пауза, чтобы не гнать цикл вхолостую
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("Long Polling остановлен")
            break
        except Exception as e:
            logger.error(f"Ошибка в polling loop: {e}")
            await asyncio.sleep(5)


def start_polling():
    """Запускает Long Polling как фоновую задачу."""
    global _polling_task
    if _polling_task is None or _polling_task.done():
        _polling_task = asyncio.create_task(polling_loop())
        logger.info("Polling task создан")


async def stop_polling():
    """Останавливает Long Polling."""
    global _polling_task
    if _polling_task:
        _polling_task.cancel()
        try:
            await _polling_task
        except asyncio.CancelledError:
            pass
        _polling_task = None