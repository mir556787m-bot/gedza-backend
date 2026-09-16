import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Ловим все сетевые запросы
        requests = []
        page.on('request', lambda r: requests.append(r.url))
        
        print('Открываем сайт...')
        await page.goto('https://gedzagroup.ru/', wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(5000)
        
        # Сохраняем HTML
        html = await page.content()
        with open('debug_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'HTML сохранён: {len(html)} символов')
        
        # Печатаем все XHR/fetch запросы
        print('\\n=== Сетевые запросы (первые 30) ===')
        for url in requests[:30]:
            print(url)
        
        await browser.close()

asyncio.run(main())