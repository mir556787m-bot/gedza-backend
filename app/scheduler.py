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

# ─── Источники меню (по приоритету) ───
MENU_SOURCE = os.getenv("MENU_SOURCE", "parser")           # parser | sellkit | iiko

# ─── SellKit ───
SELLKIT_ENABLED = os.getenv("SELLKIT_ENABLED", "false").lower() == "true" \
    or MENU_SOURCE == "sellkit"
SELLKIT_AUTH_TOKEN = os.getenv("SELLKIT_AUTH_TOKEN", "")

# ─── iiko ───
IIKO_ENABLED = os.getenv("IIKO_ENABLED", "false").lower() == "true" \
    or MENU_SOURCE == "iiko"
IIKO_API_LOGIN = os.getenv("IIKO_API_LOGIN", "")
IIKO_ORG_ID = os.getenv("IIKO_ORG_ID", "")

scheduler = AsyncIOScheduler()


# ═══════════════════════════════════════════
#  Источники меню
# ═══════════════════════════════════════════

async def _refresh_from_sellkit() -> bool:
    """Пробует получить меню через SellKit API. Возвращает True при успехе."""
    if not SELLKIT_ENABLED:
        return False
    if not SELLKIT_AUTH_TOKEN:
        logger.info("SellKit: SELLKIT_AUTH_TOKEN пуст — пропускаем")
        return False
    try:
        from app.sellkit_provider import fetch_menu_from_sellkit
        menu = await fetch_menu_from_sellkit()
        if not menu:
            logger.warning("SellKit вернул пустое меню")
            return False
        await set_menu_cache(menu)
        logger.info(f"Меню обновлено из SellKit: {len(menu)} позиций")
        return True
    except ImportError:
        logger.warning("sellkit_provider не установлен, пропускаем")
        return False
    except Exception as e:
        logger.error(f"SellKit fetch error: {e}")
        return False


async def _refresh_from_iiko() -> bool:
    """Пробует получить меню через iiko Cloud API. Возвращает True при успехе."""
    if not IIKO_ENABLED:
        return False
    if not IIKO_API_LOGIN or not IIKO_ORG_ID:
        logger.warning("iiko: не заданы IIKO_API_LOGIN / IIKO_ORG_ID")
        return False
    try:
        from app.iiko_client import fetch_menu_from_iiko
        menu = await fetch_menu_from_iiko()
        if not menu:
            logger.warning("iiko вернул пустое меню")
            return False
        await set_menu_cache(menu)
        logger.info(f"Меню обновлено из iiko: {len(menu)} позиций")
        return True
    except ImportError:
        logger.warning("iiko_client не установлен, пропускаем")
        return False
    except Exception as e:
        logger.error(f"iiko fetch error: {e}")
        return False


async def _refresh_from_parser() -> bool:
    """Fallback: парсит сайт через Playwright."""
    try:
        logger.info("Запуск парсинга меню с сайта...")
        menu = await parse_gedza_menu()
        if not menu:
            logger.warning("Парсер вернул пустой список — оставляем старый кэш")
            return False
        await set_menu_cache(menu)
        logger.info(f"Меню обновлено из парсера: {len(menu)} позиций")
        return True
    except Exception as e:
        logger.error(f"Ошибка парсера: {e}")
        return False


async def refresh_menu_job():
    """
    Основная задача: обновление меню.
    Порядок:
      1. SellKit API (если MENU_SOURCE=sellkit и есть токен)
      2. iiko API   (если MENU_SOURCE=iiko или IIKO_ENABLED=true)
      3. Playwright парсер (fallback — всегда)
    """
    if not await acquire_parse_lock(ttl=180):
        logger.info("Обновление уже идёт, пропускаем")
        return

    try:
        ok = False

        # 1. SellKit
        if not ok:
            ok = await _refresh_from_sellkit()

        # 2. iiko
        if not ok:
            ok = await _refresh_from_iiko()

        # 3. Парсер (fallback)
        if not ok:
            ok = await _refresh_from_parser()

        if not ok:
            logger.warning("Ни один источник не дал меню — оставляем старый кэш")
    except Exception as e:
        logger.error(f"Ошибка в refresh_menu_job: {e}")
    finally:
        await release_parse_lock()


async def check_stop_list_job():
    """
    Проверка стоп-листа через iiko.
    Обновляет в Redis множество ID блюд, которых нет в наличии.
    Если iiko выключен — ничего не делает.
    """
    if not IIKO_ENABLED:
        return
    try:
        from app.iiko_client import fetch_stop_list
        from app.cache import set_stop_list_cache
        stop_ids = await fetch_stop_list()
        await set_stop_list_cache(stop_ids)
        logger.info(f"Стоп-лист обновлён: {len(stop_ids)} блюд недоступны")
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Ошибка проверки стоп-листа: {e}")


# ═══════════════════════════════════════════
#  Запуск / остановка
# ═══════════════════════════════════════════

def start_scheduler():
    """Запускает планировщик."""
    logger.info(
        f"MENU_SOURCE={MENU_SOURCE}, "
        f"SellKit={'on' if SELLKIT_ENABLED else 'off'}, "
        f"iiko={'on' if IIKO_ENABLED else 'off'}, "
        f"интервал={PARSE_INTERVAL} мин"
    )

    # 1. Один раз при старте
    scheduler.add_job(
        refresh_menu_job,
        "date",
        id="initial_parse",
        replace_existing=True,
    )

    # 2. Регулярное обновление
    scheduler.add_job(
        refresh_menu_job,
        "interval",
        minutes=PARSE_INTERVAL,
        id="refresh_menu",
        replace_existing=True,
        max_instances=1,
    )

    # 3. Проверка стоп-листа (только если iiko включён)
    if IIKO_ENABLED:
        scheduler.add_job(
            check_stop_list_job,
            "interval",
            minutes=5,
            id="check_stop_list",
            replace_existing=True,
            max_instances=1,
        )
        logger.info("Задача проверки стоп-листа включена (каждые 5 мин)")

    scheduler.start()
    logger.info(f"Планировщик запущен (интервал меню {PARSE_INTERVAL} мин)")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)