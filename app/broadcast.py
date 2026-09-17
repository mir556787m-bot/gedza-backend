# app/broadcast.py
import asyncio
import logging
from typing import Optional
from app.database import get_pool
from app.max_bot import send_message

logger = logging.getLogger(__name__)

SEND_DELAY = 0.6


async def broadcast_to_all(text: str, button_text: Optional[str] = None,
                           button_url: Optional[str] = None,
                           only_consented: bool = True) -> dict:
    pool = await get_pool()

    if only_consented:
        query = "SELECT user_id FROM users WHERE consent_given = TRUE AND unsubscribed = FALSE"
    else:
        query = "SELECT user_id FROM users WHERE unsubscribed = FALSE"

    async with pool.acquire() as conn:
        rows = await conn.fetch(query)
        broadcast_id = await conn.fetchval(
            "INSERT INTO broadcasts (text, recipients_count) VALUES ($1, $2) RETURNING id",
            text, len(rows),
        )

    total = len(rows)
    sent, failed = 0, 0
    logger.info(f"Broadcast #{broadcast_id}: {total} recipients")

    buttons = None
    if button_text and button_url:
        buttons = [[{"type": "open_app", "text": button_text, "web_app": button_url}]]

    for row in rows:
        ok = await send_message(row["user_id"], text, buttons)
        if ok:
            sent += 1
        else:
            failed += 1
        await asyncio.sleep(SEND_DELAY)

    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE broadcasts SET sent_count = $1, failed_count = $2, completed_at = NOW() WHERE id = $3",
            sent, failed, broadcast_id,
        )

    logger.info(f"Broadcast #{broadcast_id} done: sent={sent}, failed={failed}")
    return {"broadcast_id": broadcast_id, "total": total, "sent": sent, "failed": failed}