# app/clear_webhook.py
"""Удаляет ВСЕ webhook-подписки с бота через MAX API."""
import asyncio
import httpx
from app.config import settings


async def main():
    async with httpx.AsyncClient(verify=False, timeout=15) as c:
        headers = {"Authorization": settings.MAX_BOT_TOKEN}
        base = settings.MAX_API_URL

        # 1. Получаем все подписки
        r = await c.get(f"{base}/subscriptions", headers=headers)
        print(f"Всего подписок: {r.status_code}")
        data = r.json()
        subscriptions = data.get("subscriptions", [])
        print(f"Найдено: {len(subscriptions)}")

        # 2. Удаляем каждую по URL
        for sub in subscriptions:
            url = sub.get("url")
            if not url:
                continue
            print(f"\nУдаляю: {url}")
            # MAX API требует URL в query-параметре
            r = await c.delete(
                f"{base}/subscriptions",
                params={"url": url},
                headers=headers,
            )
            print(f"  → {r.status_code} {r.text[:200]}")

        # 3. Проверяем результат
        r = await c.get(f"{base}/subscriptions", headers=headers)
        print(f"\nПосле удаления: {r.status_code} {r.text}")


if __name__ == "__main__":
    asyncio.run(main())
