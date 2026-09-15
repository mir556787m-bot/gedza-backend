import asyncio
from app.parser import parse_gedza_menu


async def main():
    items = await parse_gedza_menu()
    print(f"\n=== Найдено: {len(items)} позиций ===\n")
    for item in items[:15]:
        print(f"* {item['name']} -- {item['price']} руб.")
        if item.get('description'):
            print(f"  {item['description'][:80]}")


if __name__ == "__main__":
    asyncio.run(main())