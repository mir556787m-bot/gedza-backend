# app/parser.py
import logging
import os
import re
import hashlib
from typing import List, Dict

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

GEDZA_URL = os.getenv("GEDZA_URL", "https://gedzagroup.ru/")


def _slugify(text: str) -> str:
    """Преобразует название в стабильный slug-id (латиница + цифры)."""
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


def _stable_plate_id(name: str, category: str) -> str:
    """
    Стабильный SellKit-совместимый plateID.
    Один и тот же товар → всегда один и тот же ID при каждом парсинге.
    Формула: MD5(category::name) → 6-значное число (100000..999999).
    """
    raw = f"{category}::{name}".encode("utf-8")
    h = int(hashlib.md5(raw).hexdigest()[:8], 16)
    return str(h % 900000 + 100000)


def _clean_text(text: str) -> str:
    """Очищает текст от мусора."""
    if not text:
        return ""
    t = str(text)
    t = re.sub(r'[\*_]', '', t)
    t = re.sub(r'[ \t]+', ' ', t)
    t = re.sub(r'г\s*г', 'г', t)
    t = re.sub(r'\n{3,}', '\n\n', t)
    return t.strip()


def _split_description(text: str) -> str:
    """Вставляет \\n\\n перед смысловыми блоками в описании."""
    if not text:
        return ""
    text = re.sub(r'\s*Годен в течении', '\n\nГоден в течении', text)
    text = re.sub(r'\s*Изображение на сайте', '\n\nИзображение на сайте', text)
    text = re.sub(r'\s*(Состав[:\s—-])', '\n\nСостав: ', text)
    text = re.sub(r'\s*(Ккал|Белки|Жиры|Углеводы)', r'\n\n\1', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


async def parse_gedza_menu() -> List[Dict]:
    """
    Парсит меню с сайта Гедзы.
    Возвращает список блюд, каждое содержит поля двух форматов:
    - внутренний (id, name, price, image, weight, category) — для текущего фронта
    - SellKit-совместимый (plateID, plateName, cleanPrice, thumbnailPicture,
      mass, categoryName, sku) — для корзины
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

            for _ in range(30):
                await page.mouse.wheel(0, 3000)
                await page.wait_for_timeout(400)
            await page.wait_for_timeout(3000)

            items = await page.evaluate("""() => {
                const result = [];
                const seen = new Set();

                const sections = Array.from(document.querySelectorAll('div'))
                    .filter(el => {
                        const cls = el.className || '';
                        return cls.includes('border-b') && cls.includes('last:border-none');
                    });

                sections.forEach(section => {
                    const h2 = section.querySelector('h2');
                    if (!h2) return;
                    const category = (h2.innerText || '').trim();
                    if (!category) return;

                    const cards = section.querySelectorAll('[class*="shadow-productCart"]');

                    cards.forEach(el => {
                        const img = el.querySelector('img[title]');
                        if (!img) return;

                        const name = (img.getAttribute('title') || '').trim();
                        if (!name || name.length < 3) return;

                        const key = category + '::' + name;
                        if (seen.has(key)) return;
                        seen.add(key);

                        const imageSrc = img.getAttribute('src') || '';

                        // Вес
                        let weight = '';
                        el.querySelectorAll('p').forEach(p => {
                            const t = (p.innerText || '').trim();
                            if (/^\\d+\\s*г(р)?$/.test(t)) weight = t;
                        });

                        // Старая цена
                        let oldPrice = 0;
                        const oldEl = el.querySelector('[class*="line-through"]');
                        if (oldEl) {
                            const m = (oldEl.innerText || '').match(/(\\d[\\d\\s]*)/);
                            if (m) oldPrice = parseInt(m[1].replace(/\\s/g, ''));
                        }

                        // Цены
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

                        // Бейдж
                        let badge = '';
                        const badgeImg = el.querySelector('img[data-tooltip-content]');
                        if (badgeImg) {
                            const b = (badgeImg.getAttribute('data-tooltip-content') || '').toLowerCase();
                            if (b.includes('остр')) badge = 'ОСТРО';
                            else if (b.includes('хит')) badge = 'ХИТ';
                            else if (b.includes('нов')) badge = 'НОВИНКА';
                            else if (b.includes('акц')) badge = 'АКЦИЯ';
                            else badge = b.toUpperCase();
                        }

                        // Описание
                        const descParts = [];
                        el.querySelectorAll('p').forEach(p => {
                            const t = (p.innerText || '').trim();
                            if (t.length > 20 && !t.includes('₽') && !/^\\d+\\s*г/.test(t)) {
                                descParts.push({
                                    text: t,
                                    html: p.innerHTML || ''
                                });
                            }
                        });

                        let description = '';
                        if (descParts.length === 1) {
                            const html = descParts[0].html;
                            if (html.includes('<br')) {
                                description = html
                                    .replace(/<br\\s*\\/?>/gi, '\\n\\n')
                                    .replace(/<[^>]+>/g, '')
                                    .replace(/\\n{3,}/g, '\\n\\n')
                                    .trim();
                            } else {
                                description = descParts[0].text;
                            }
                        } else if (descParts.length > 1) {
                            description = descParts.map(d => d.text).join('\\n\\n');
                        }

                        if (name && price > 0) {
                            result.push({
                                id: 'tmp_' + result.length,
                                name: name,
                                description: description,
                                price: price,
                                old_price: oldPrice || null,
                                weight: weight || null,
                                category: category,
                                badge: badge || null,
                                image: imageSrc,
                            });
                        }
                    });
                });

                return result;
            }""")

            # Очистка + разбивка описания + id + plateID
            seen_ids = set()
            for item in items:
                item["name"] = _clean_text(item["name"])
                item["description"] = _clean_text(item["description"])
                item["description"] = _split_description(item["description"])
                if item["weight"]:
                    item["weight"] = _clean_text(item["weight"])

                # ─── slug-id (внутренний) ───
                base_id = _slugify(item["name"])
                item_id = base_id
                counter = 1
                while item_id in seen_ids:
                    counter += 1
                    item_id = f"{base_id}_{counter}"
                seen_ids.add(item_id)
                item["id"] = item_id

                # ─── НОВОЕ: SellKit-совместимые поля ───
                plate_id = _stable_plate_id(item["name"], item["category"])
                item["plateID"] = plate_id
                item["plateName"] = item["name"]
                item["cleanPrice"] = str(item["price"])
                item["thumbnailPicture"] = item["image"]
                item["mass"] = item["weight"] or ""
                item["categoryName"] = item["category"]
                item["sku"] = plate_id  # совпадает с plateID

            logger.info(f"Найдено {len(items)} позиций")

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