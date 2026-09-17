# app/orders.py
import json
import logging
from typing import List, Dict
from app.database import get_pool

logger = logging.getLogger(__name__)


async def create_order(order_id: str, user_id: int, total: float, items: List[Dict],
                       address: str = "", phone: str = "", comment: str = "") -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO orders (order_id, user_id, total, items, address, phone, comment)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, order_id, user_id, total, json.dumps(items, ensure_ascii=False),
             address, phone, comment)
    logger.info(f"Order {order_id} saved to DB")
    return True


async def get_user_orders(user_id: int, limit: int = 10) -> list:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT order_id, total, status, created_at FROM orders
            WHERE user_id = $1
            ORDER BY created_at DESC LIMIT $2
        """, user_id, limit)
        return [
            {
                "order_id": r["order_id"],
                "total": float(r["total"]),
                "status": r["status"],
                "created_at": r["created_at"].isoformat(),
            }
            for r in rows
        ]