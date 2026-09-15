# app/scheduler.py
import logging
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.cache import (
    acquire_parse_lock,
    release_parse_lock,
    set_menu_cache,
    get_menu_cache,
)
from app.parser import parse_gedza_menu

logger = logging.getLogger(__name__)

PARSE_INTERVAL = int(os.getenv("PARSE_INTERVAL_MINUTES", "60"))

scheduler = AsyncIOScheduler()


async def refresh_menu_job():
    """Фоновая задача: парсит меню и обновляет Redis."""
    if not await acquire_parse_lock(ttl=120):
        logger.info("Парсинг уже идёт, пропускаем")
        return

    try:
        logger.info("Запуск парсинга меню...")
        menu = await parse_gedza_menu()

        if not menu:
            logger.warning("Парсер вернул пустой список — оставляем старый кэш")
            return

        await set_menu_cache(menu)
        logger.info(f"Меню обновлено: {len(menu)} позиций")
    except Exception as e:
        logger.error(f"Ошибка в refresh_menu_job: {e}")
    finally:
        await release_parse_lock()


def start_scheduler():
    """Запускает планировщик."""
    # Раз в N минут — обновление
    scheduler.add_job(
        refresh_menu_job,
        "interval",
        minutes=PARSE_INTERVAL,
        id="refresh_menu",
        replace_existing=True,
        max_instances=1,
    )

    # При старте — один раз сразу
    scheduler.add_job(
        refresh_menu_job,
        "date",
        id="initial_parse",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(f"Планировщик запущен (интервал {PARSE_INTERVAL} мин)")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)