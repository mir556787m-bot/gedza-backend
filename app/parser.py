# app/parser.py
import logging
import os
import re
from typing import List, Dict

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

GEDZA_URL = os.getenv("GEDZA_URL", "https://gedzagroup.ru/")


def _slugify(text: str) -> str:
    """Преобразует название в стабильный slug-id."""
    import re
    text = text.lower().strip()
    text = re.sub(r"[^a-zа-я0-9]+", "_", text)
    return text.strip("_")[:50]


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

            # Прокручиваем страницу вниз, чтобы подгрузились все карточки
            for _ in range(8):
                await page.mouse.wheel(0, 3000)
                await page.wait_for_timeout(500)
            await page.wait_for_timeout(2000)

            items = await page.evaluate("""() => {
                const items = [];
                const seen = new Set();

                // Пытаемся найти все карточки товаров
                // Ищем по разным селекторам: ProductCard, Card, [class*="product"]
                const cards = document.querySelectorAll(
                    '[class*="ProductCard"], [class*="product-card"], [class*="Product"]'
                );

                cards.forEach((el, idx) => {
                    // Ищем картинку с названием в title
                    const img = el.querySelector('img[title]') || el.querySelector('img');
                    if (!img) return;

                    const name = img.getAttribute('title') || img.getAttribute('alt') || '';
                    if (!name || name.length < 3) return;
                    if (seen.has(name)) return;

                    const imgSrc = img.getAttribute('src') || '';

                    // Весь текст карточки
                    const allText = (el.innerText || '').trim();

                    // ─── Цены ───
                    // Все найденные "числа + ₽"
                    const priceMatches = [...allText.matchAll(/(\\d[\\d\\s]*)\\s*₽/g)]
                        .map(m => parseInt(m[1].replace(/\\s/g, '')))
                        .filter(n => n > 0);

                    let price = 0;
                    let oldPrice = 0;

                    // Ищем элемент с line-through для старой цены
                    const oldPriceEl = el.querySelector(
                        '[style*="line-through"], .old-price, [class*="old"], s, del'
                    );
                    if (oldPriceEl) {
                        const oldText = (oldPriceEl.innerText || '').replace(/[^\\d]/g, '');
                        if (oldText) oldPrice = parseInt(oldText);
                    }

                    if (priceMatches.length === 1) {
                        price = priceMatches[0];
                    } else if (priceMatches.length >= 2) {
                        // Обычно [старая, новая] или [новая, старая]
                        price = Math.min(...priceMatches);
                        oldPrice = Math.max(...priceMatches);
                    }

                    // ─── Вес ───
                    let weight = '';
                    const weightMatch = allText.match(/(\\d+)\\s*г(?:р)?\\b/i);
                    if (weightMatch) weight = weightMatch[1] + ' г';

                    // ─── Бейдж ───
                    let badge = '';
                    const upper = allText.toUpperCase();
                    if (upper.includes('НОВИНКА')) badge = 'НОВИНКА';
                    else if (upper.includes('ХИТ')) badge = 'ХИТ';
                    else if (upper.includes('ОСТРО') || upper.includes('🌶')) badge = 'ОСТРО';

                    // ─── Описание ───
                    let description = '';
                    const descEl = el.querySelector(
                        '[class*="description"], [class*="Description"], span.block'
                    );
                    if (descEl) {
                        description = descEl.innerText.trim();
                    } else {
                        // Иначе — из всего текста берём первые 200 символов после названия
                        const cleanText = allText
                            .replace(priceMatch => priceMatch, '')
                            .split('\\n')
                            .map(s => s.trim())
                            .filter(s => s.length > 10 && !s.includes('₽') && !s.includes('г'))
                            .join(' ');
                        description = cleanText.substring(0, 200);
                    }

                    // ─── Категория ───
                    // Ищем ближайший заголовок раздела или data-атрибут
                    let category = '';
                    const catAttr = el.getAttribute('data-category')
                        || el.closest('[data-category]')?.getAttribute('data-category');
                    if (catAttr) {
                        category = catAttr;
                    } else {
                        // Ищем заголовок выше в DOM
                        let parent = el.parentElement;
                        for (let i = 0; i < 6 && parent; i++) {
                            const h = parent.querySelector('h1, h2, h3');
                            if (h && h.innerText.trim().length < 60) {
                                category = h.innerText.trim();
                                break;
                            }
                            parent = parent.parentElement;
                        }
                    }

                    if (name && price > 0) {
                        seen.add(name);
                        items.push({
                            id: 'gedza_' + idx,
                            name: name,
                            description: description,
                            price: price,
                            old_price: oldPrice || null,
                            weight: weight || null,
                            category: category || null,
                            badge: badge || null,
                            image: imgSrc,
                        });
                    }
                });

                return items;
            }""")

            # Slug-id на основе названия
            for item in items:
                item["id"] = _slugify(item["name"])

            logger.info(f"Найдено {len(items)} позиций")
            return items

        except Exception as e:
            logger.error(f"Ошибка парсинга: {e}")
            return []
        finally:
            await browser.close()