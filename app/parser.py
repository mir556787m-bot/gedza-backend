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

            # Прокручиваем страницу — подгружаем все карточки
            for _ in range(15):
                await page.mouse.wheel(0, 3000)
                await page.wait_for_timeout(500)
            await page.wait_for_timeout(3000)

            items = await page.evaluate("""() => {
                const items = [];
                const seen = new Set();

                // Обработка одной карточки
                const processCard = (el, category) => {
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

                    // Старая цена — элемент с классом line-through
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

                    // Если old_price === price — сбрасываем старую цену
                    if (oldPrice && oldPrice <= price) oldPrice = 0;

                    // Бейдж — img с data-tooltip-content
                    let badge = '';
                    const badgeImg = el.querySelector('img[data-tooltip-content]');
                    if (badgeImg) {
                        badge = (badgeImg.getAttribute('data-tooltip-content') || '').toUpperCase();
                    }

                    // Описание — длинный <p> без цены/веса
                    let description = '';
                    el.querySelectorAll('p').forEach(p => {
                        const t = (p.innerText || '').trim();
                        if (t.length > 40 && !t.includes('₽') && !/^\\d+\\s*г/.test(t)) {
                            description = t;
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
                            category: category || null,
                            badge: badge || null,
                            image: imageSrc,
                        });
                    }
                };

                // 1. Идём по всем секциям (section-XX) и берём заголовок как категорию
                const sections = document.querySelectorAll('[class*="section-"]');
                sections.forEach(section => {
                    let category = '';
                    const h = section.querySelector('h1, h2, h3');
                    if (h) {
                        category = (h.innerText || '').trim().slice(0, 50);
                    }

                    // Карточки внутри секции
                    const cards = section.querySelectorAll('[class*="shadow-productCart"]');
                    cards.forEach(card => processCard(card, category));
                });

                // 2. Fallback: если категорий нет — берём все карточки без категории
                if (items.length === 0) {
                    const allCards = document.querySelectorAll('[class*="shadow-productCart"]');
                    allCards.forEach(card => processCard(card, 'Меню'));
                }

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