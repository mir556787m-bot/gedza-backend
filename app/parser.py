# app/parser.py
import logging
import os
from typing import List, Dict

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

GEDZA_URL = os.getenv("GEDZA_URL", "https://gedzagroup.ru/")


async def parse_gedza_menu() -> List[Dict]:
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
            await page.goto(GEDZA_URL, wait_until="networkidle", timeout=45000)
            await page.wait_for_timeout(3000)

            items = await page.evaluate("""() => {
                const items = [];
                const cards = document.querySelectorAll('[class*="ProductCard"]');
                const seen = new Set();
                cards.forEach((el, idx) => {
                    const img = el.querySelector('img[title]');
                    if (!img) return;
                    const name = img.getAttribute('title') || '';
                    if (!name || seen.has(name)) return;
                    const imgSrc = img.getAttribute('src') || '';
                    let price = 0;
                    const allText = el.innerText || '';
                    const priceMatch = allText.match(/(\\d[\\d\\s]*)\\s*₽/);
                    if (priceMatch) {
                        price = parseInt(priceMatch[1].replace(/\\s/g, ''));
                    }
                    const descEl = el.querySelector('span.block');
                    const description = descEl ? descEl.innerText.trim() : '';
                    if (name && price > 0) {
                        seen.add(name);
                        items.push({
                            id: 'gedza_' + idx,
                            name: name,
                            description: description,
                            price: price,
                            image: imgSrc,
                            category: 'Меню'
                        });
                    }
                });
                return items;
            }""")

            logger.info(f"Найдено {len(items)} позиций")
            return items
        except Exception as e:
            logger.error(f"Ошибка парсинга: {e}")
            return []
        finally:
            await browser.close()