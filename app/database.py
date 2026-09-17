# app/database.py
import logging
from typing import Optional
import asyncpg
from app.config import settings

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.POSTGRES_URL,
            min_size=2,
            max_size=10,
            command_timeout=10,
        )
        logger.info("PostgreSQL pool created")
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("PostgreSQL pool closed")


async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id         BIGINT PRIMARY KEY,
                first_name      VARCHAR(255),
                last_name       VARCHAR(255),
                username        VARCHAR(255),
                subscribed_at   TIMESTAMP DEFAULT NOW(),
                last_seen       TIMESTAMP DEFAULT NOW(),
                consent_given   BOOLEAN DEFAULT FALSE,
                consent_date    TIMESTAMP,
                unsubscribed    BOOLEAN DEFAULT FALSE,
                restaurant_id   INTEGER DEFAULT 1
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id              SERIAL PRIMARY KEY,
                order_id        VARCHAR(50) UNIQUE NOT NULL,
                user_id         BIGINT NOT NULL,
                total           NUMERIC(10, 2) NOT NULL,
                items           JSONB NOT NULL,
                address         TEXT,
                phone           VARCHAR(50),
                comment         TEXT,
                status          VARCHAR(50) DEFAULT 'created',
                created_at      TIMESTAMP DEFAULT NOW(),
                updated_at      TIMESTAMP DEFAULT NOW(),
                restaurant_id   INTEGER DEFAULT 1
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS cart_events (
                id              SERIAL PRIMARY KEY,
                user_id         BIGINT NOT NULL,
                item_id         VARCHAR(50),
                action          VARCHAR(20),
                quantity        INTEGER,
                created_at      TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS broadcasts (
                id              SERIAL PRIMARY KEY,
                text            TEXT NOT NULL,
                recipients_count INTEGER,
                sent_count      INTEGER,
                failed_count    INTEGER,
                created_at      TIMESTAMP DEFAULT NOW(),
                completed_at    TIMESTAMP
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS restaurants (
                id              SERIAL PRIMARY KEY,
                name            VARCHAR(255) NOT NULL,
                slug            VARCHAR(100) UNIQUE NOT NULL,
                bot_token       VARCHAR(255),
                menu_url        VARCHAR(500),
                is_active       BOOLEAN DEFAULT TRUE,
                created_at      TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_user ON orders (user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders (status)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_consent ON users (consent_given, unsubscribed)")

    logger.info("Database initialized: 5 tables ready")