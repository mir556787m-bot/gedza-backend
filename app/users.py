# app/users.py
import logging
from typing import Optional
from app.database import get_pool

logger = logging.getLogger(__name__)


async def upsert_user(user_id: int, first_name=None, last_name=None, username=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (user_id, first_name, last_name, username, last_seen)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                first_name = COALESCE(EXCLUDED.first_name, users.first_name),
                last_name  = COALESCE(EXCLUDED.last_name, users.last_name),
                username   = COALESCE(EXCLUDED.username, users.username),
                last_seen  = NOW()
        """, user_id, first_name, last_name, username)


async def get_user(user_id: int) -> Optional[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
        return dict(row) if row else None


async def give_consent(user_id: int) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET consent_given = TRUE, consent_date = NOW() WHERE user_id = $1",
            user_id,
        )
    return True


async def unsubscribe(user_id: int) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET unsubscribed = TRUE WHERE user_id = $1", user_id
        )
    return True


async def get_all_subscribed() -> list:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT user_id FROM users
            WHERE consent_given = TRUE AND unsubscribed = FALSE
        """)
        return [r["user_id"] for r in rows]