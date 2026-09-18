# app/parser.py
import logging
import os
import re
from typing import List, Dict

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

GEDZA_URL = os.getenv("GEDZA_URL", "https://gedzagroup.ru/")


def _slugify(text: str) -> str:
    """Преобразует название в стабильный slug-id (латиница + цифры)."""
    # Транслитерация русских букв
    translit = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    }
    text = text.lower().strip()
    result = ''
    for char in text:
        result += translit.get(char, char)
    result = re.sub(r"[^a-z0-9]+", "_", result)
    return result.strip("_")[:50]


def _detect_category(name: str) -> str:
    """Определяет категорию по названию товара."""
    n = name.lower()

    # Комбо — проверяем первым (часто включает в себя другие слова)
    if 'комбо' in n:
        return 'Комбо'

    # Пицца
    if 'пицца' in n:
        return 'Пицца'

    # Сеты (проверяем до роллов)
    if n.startswith('сет ') or ' сет ' in n:
        return 'Сеты'

    # Роллы, суши
    if 'ролл' in n or 'суши' in n:
        return 'Роллы'

    # Закуски
    if any(w in n for w in ['крыл', 'нагетс', 'закуск', 'палочк', 'картоф', 'фри', 'луковые']):
        return 'Закуски'

    # Горячее
    if any(w in n for w in ['горячее', 'шашлык', 'стейк']):
        return 'Горячее'

    # Супы
    if any(w in n for w in ['суп', 'том-ям', 'том ям', 'борщ']):
        return 'Супы'

    # Салаты
    if 'салат' in n:
        return 'Салаты'

    # Десерты
    if any(w in n for w in ['десерт', 'пончик', 'чизкейк', 'торт', 'мороженое', 'пирожное']):
        return 'Десерты'

    # Напитки
    if any(w in n for w in ['напиток', 'кола', 'лимонад', 'морс', 'сок', 'чай', 'кофе', 'вода']):
        return 'Напитки'

    # Соусы
    if any(w in n for w in ['соус', 'кетчуп', 'майонез']):
        return 'Соусы'

    # По умолчанию
    return 'Прочее'


async def parse_gedza_menu() -> List[Dict]:
    """
    Парсит меню с сайта Гедзы.
    Извлекает: id, name, price, old_price, weight, category, badge, description, image.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="ru-RU",
        )
        page = await context.new_page()

        try:
            logger.info(f"Открываем {GEDZA_URL}")
            await page.goto(GEDZA_URL, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(4000)

            # Прокручиваем страницу вниз — подгружаем все карточки
            for _ in range(20):
                await page.mouse.wheel(0, 3000)
                await page.wait_for_timeout(500)
            await page.wait_for_timeout(3000)

            items = await page.evaluate("""() => {
                const items = [];
                const seen = new Set();

                // Находим все карточки по классу с shadow-productCart
                const cards = document.querySelectorAll('[class*="shadow-productCart"]');

                cards.forEach(el => {
                    const img = el.querySelector('img[title]');
                    if (!img) return;

                    const name = (img.getAttribute('title') || '').trim();
                    if (!name || name.length < 3 || seen.has(name)) return;

                    const imageSrc = img.getAttribute('src') || '';

                    // Вес — <p> с текстом "NNN г"
                    let weight = '';
                    el.querySelectorAll('p').forEach(p => {
                        const t = (p.innerText || '').trim();
                        if (/^\\d+\\s*г(р)?$/.test(t)) weight = t;
                    });

                    // Старая цена — элемент с line-through
                    let oldPrice = 0;
                    const oldEl = el.querySelector('[class*="line-through"]');
                    if (oldEl) {
                        const m = (oldEl.innerText || '').match(/(\\d[\\d\\s]*)/);
                        if (m) oldPrice = parseInt(m[1].replace(/\\s/g, ''));
                    }

                    // Цены — все <p> с "₽"
                    const prices = [];
                    el.querySelectorAll('p').forEach(p => {
                        const t = (p.innerText || '').trim();
                        const m = t.match(/^(\\d[\\d\\s]*)\\s*₽/);
                        if (m) prices.push(parseInt(m[1].replace(/\\s/g, '')));
                    });

                    let price = 0;
                    if (prices.length === 1) {
                        price = prices[0];
                    } else if (prices.length >= 2) {
                        price = Math.min(...prices);
                        if (!oldPrice) oldPrice = Math.max(...prices);
                    }

                    if (oldPrice && oldPrice <= price) oldPrice = 0;

                    // Бейдж — img с data-tooltip-content
                    let badge = '';
                    const badgeImg = el.querySelector('img[data-tooltip-content]');
                    if (badgeImg) {
                        const b = (badgeImg.getAttribute('data-tooltip-content') || '').toLowerCase();
                        if (b.includes('остр')) badge = 'ОСТРО';
                        else if (b.includes('хит')) badge = 'ХИТ';
                        else if (b.includes('нов')) badge = 'НОВИНКА';
                        else badge = b.toUpperCase();
                    }

                    // Описание — длинный <p> без цены/веса
                    let description = '';
                    el.querySelectorAll('p').forEach(p => {
                        const t = (p.innerText || '').trim();
                        if (t.length > 40 && !t.includes('₽') && !/^\\d+\\s*г/.test(t)) {
                            if (!description) description = t;
                        }
                    });

                    if (name && price > 0) {
                        seen.add(name);
                        items.push({
                            id: 'tmp_' + items.length,
                            name: name,
                            description: description,
                            price: price,
                            old_price: oldPrice || null,
                            weight: weight || null,
                            category: null,   // заполним на Python
                            badge: badge || null,
                            image: imageSrc,
                        });
                    }
                });

                return items;
            }""")

            # Заполняем id и категорию на стороне Python
            for item in items:
                item["id"] = _slugify(item["name"])
                item["category"] = _detect_category(item["name"])

            logger.info(f"Найдено {len(items)} позиций")

            # Логируем распределение по категориям
            cats = {}
            for item in items:
                cats[item["category"]] = cats.get(item["category"], 0) + 1
            logger.info(f"Категории: {cats}")

            return items

        except Exception as e:
            logger.error(f"Ошибка парсинга: {e}")
            return []
        finally:
            await browser.close()