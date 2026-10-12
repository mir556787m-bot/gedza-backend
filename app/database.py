# app/database.py
import json
import logging
import os
from typing import Optional, List

import asyncpg

logger = logging.getLogger(__name__)

POSTGRES_URL = os.getenv(
    "POSTGRES_URL",
    "postgresql://gedza:gedza@localhost:5432/gedza",
)

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            POSTGRES_URL,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )
        logger.info("PostgreSQL pool created")
    return _pool


async def close_pool():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("PostgreSQL pool closed")


async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id              BIGSERIAL PRIMARY KEY,
                user_id         BIGINT UNIQUE NOT NULL,
                name            VARCHAR(255),
                username        VARCHAR(255),
                first_name      VARCHAR(255),
                last_name       VARCHAR(255),
                phone           VARCHAR(50),
                address         TEXT,
                address_details JSONB,
                legal_agreed    BOOLEAN DEFAULT FALSE,
                consent_given   BOOLEAN DEFAULT FALSE,
                consent_date    TIMESTAMP,
                unsubscribed    BOOLEAN DEFAULT FALSE,
                last_seen       TIMESTAMP,
                restaurant_id   INTEGER,
                created_at      TIMESTAMP DEFAULT NOW(),
                updated_at      TIMESTAMP DEFAULT NOW()
            )
        """)

        _user_migrations = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(255)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(50)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS address TEXT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS address_details JSONB",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS legal_agreed BOOLEAN DEFAULT FALSE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS restaurant_id INTEGER",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(255)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS first_name VARCHAR(255)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_name VARCHAR(255)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS consent_given BOOLEAN DEFAULT FALSE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS consent_date TIMESTAMP",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS unsubscribed BOOLEAN DEFAULT FALSE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_seen TIMESTAMP",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()",
        ]
        for sql in _user_migrations:
            try:
                await conn.execute(sql)
            except Exception as e:
                logger.warning(f"User migration skipped: {e}")

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id              BIGSERIAL PRIMARY KEY,
                order_id        VARCHAR(50) UNIQUE NOT NULL,
                user_id         BIGINT NOT NULL,
                total           NUMERIC(10, 2) NOT NULL,
                items           JSONB NOT NULL,
                address         TEXT,
                phone           VARCHAR(50),
                comment         TEXT,
                status          VARCHAR(50) DEFAULT 'new',
                created_at      TIMESTAMP DEFAULT NOW(),
                updated_at      TIMESTAMP DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS cart_events (
                id              BIGSERIAL PRIMARY KEY,
                user_id         BIGINT NOT NULL,
                item_id         VARCHAR(255),
                action          VARCHAR(50),
                created_at      TIMESTAMP DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS broadcasts (
                id              BIGSERIAL PRIMARY KEY,
                text            TEXT NOT NULL,
                recipients_count INTEGER DEFAULT 0,
                sent_count      INTEGER DEFAULT 0,
                failed_count    INTEGER DEFAULT 0,
                created_at      TIMESTAMP DEFAULT NOW(),
                completed_at    TIMESTAMP
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS restaurants (
                id              SERIAL PRIMARY KEY,
                name            VARCHAR(255) NOT NULL,
                address         TEXT,
                phone           VARCHAR(50),
                is_active       BOOLEAN DEFAULT TRUE,
                created_at      TIMESTAMP DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                user_id         BIGINT PRIMARY KEY,
                delivery_type   VARCHAR(20) DEFAULT 'delivery',
                address         TEXT,
                address_details JSONB,
                updated_at      TIMESTAMP DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_addresses (
                id              SERIAL PRIMARY KEY,
                user_id         BIGINT NOT NULL,
                address         TEXT NOT NULL,
                address_details JSONB,
                is_default      BOOLEAN DEFAULT FALSE,
                created_at      TIMESTAMP DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS wheel_prizes (
                id              SERIAL PRIMARY KEY,
                name            VARCHAR(255) NOT NULL,
                weight          INTEGER DEFAULT 1,
                is_active       BOOLEAN DEFAULT TRUE
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS wheel_spins (
                id              SERIAL PRIMARY KEY,
                user_id         BIGINT NOT NULL,
                prize_id        INTEGER,
                prize_name      VARCHAR(255),
                created_at      TIMESTAMP DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS promocodes (
                id              SERIAL PRIMARY KEY,
                code            VARCHAR(50) UNIQUE NOT NULL,
                discount        INTEGER DEFAULT 0,
                percent         INTEGER DEFAULT 0,
                min_order       INTEGER DEFAULT 0,
                is_active       BOOLEAN DEFAULT TRUE,
                description     VARCHAR(255)
            )
        """)

        _promo_migrations = [
            "ALTER TABLE promocodes ADD COLUMN IF NOT EXISTS sale_type VARCHAR(50) DEFAULT 'price'",
            "ALTER TABLE promocodes ADD COLUMN IF NOT EXISTS promocode_type INTEGER DEFAULT 0",
            "ALTER TABLE promocodes ADD COLUMN IF NOT EXISTS can_sum_with_other_promos BOOLEAN DEFAULT TRUE",
            "ALTER TABLE promocodes ADD COLUMN IF NOT EXISTS can_sum_with_gifts BOOLEAN DEFAULT TRUE",
            "ALTER TABLE promocodes ADD COLUMN IF NOT EXISTS can_sum_with_bonuses BOOLEAN DEFAULT TRUE",
            "ALTER TABLE promocodes ADD COLUMN IF NOT EXISTS gift_ids TEXT DEFAULT ''",
            "ALTER TABLE promocodes ADD COLUMN IF NOT EXISTS gift_name VARCHAR(255)",
            "ALTER TABLE promocodes ADD COLUMN IF NOT EXISTS gift_picture TEXT",
            "ALTER TABLE promocodes ADD COLUMN IF NOT EXISTS delivery_types VARCHAR(20) DEFAULT '2'",
            "ALTER TABLE promocodes ADD COLUMN IF NOT EXISTS auto_activate BOOLEAN DEFAULT FALSE",
            "ALTER TABLE promocodes ADD COLUMN IF NOT EXISTS min_cart_price INTEGER DEFAULT 0",
            "ALTER TABLE promocodes ADD COLUMN IF NOT EXISTS title VARCHAR(255)",
            "ALTER TABLE promocodes ADD COLUMN IF NOT EXISTS short_description VARCHAR(255)",
            "ALTER TABLE promocodes ADD COLUMN IF NOT EXISTS tag VARCHAR(50)",
            "ALTER TABLE promocodes ADD COLUMN IF NOT EXISTS category_name VARCHAR(255)",
            "ALTER TABLE promocodes ADD COLUMN IF NOT EXISTS applies_to_category_only BOOLEAN DEFAULT FALSE",
            "ALTER TABLE promocodes ADD COLUMN IF NOT EXISTS is_hidden BOOLEAN DEFAULT FALSE",
        ]
        for sql in _promo_migrations:
            try:
                await conn.execute(sql)
            except Exception as e:
                logger.warning(f"Promo migration skipped: {e}")

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_payment_settings (
                user_id         BIGINT PRIMARY KEY,
                payment_type    VARCHAR(50) DEFAULT 'card_on_delivery',
                updated_at      TIMESTAMP DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_order_time (
                user_id         BIGINT PRIMARY KEY,
                order_time      VARCHAR(100) DEFAULT 'now',
                updated_at      TIMESTAMP DEFAULT NOW()
            )
        """)

        await conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_user ON orders (user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders (status)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_consent ON users (consent_given, unsubscribed)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_wheel_spins_user ON wheel_spins (user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_user_addresses_user ON user_addresses (user_id)")

    logger.info("Database initialized: 12 tables ready")


def _to_json_str(value):
    if value is None:
        return None
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _parse_jsonb(value):
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return value
    return value


async def upsert_session(user_id, delivery_type, address, address_details=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO user_sessions (user_id, delivery_type, address, address_details, updated_at)
            VALUES ($1, $2, $3, $4::jsonb, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                delivery_type   = EXCLUDED.delivery_type,
                address         = EXCLUDED.address,
                address_details = EXCLUDED.address_details,
                updated_at      = NOW()
            RETURNING user_id, delivery_type, address, address_details, updated_at
            """,
            user_id, delivery_type, address, _to_json_str(address_details),
        )
        if not row:
            return None
        result = dict(row)
        result["address_details"] = _parse_jsonb(result["address_details"])
        return result


async def get_session(user_id: int) -> Optional[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT user_id, delivery_type, address, address_details, updated_at "
            "FROM user_sessions WHERE user_id = $1",
            user_id,
        )
        if not row:
            return None
        result = dict(row)
        result["address_details"] = _parse_jsonb(result["address_details"])
        return result


async def get_user_addresses(user_id: int) -> List[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, user_id, address, address_details, is_default, created_at "
            "FROM user_addresses WHERE user_id = $1 ORDER BY is_default DESC, created_at DESC",
            user_id,
        )
        result = []
        for r in rows:
            item = dict(r)
            item["address_details"] = _parse_jsonb(item["address_details"])
            result.append(item)
        return result


async def add_user_address(user_id, address, address_details=None, is_default=False):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if is_default:
            await conn.execute(
                "UPDATE user_addresses SET is_default = FALSE WHERE user_id = $1",
                user_id,
            )
        row = await conn.fetchrow(
            """
            INSERT INTO user_addresses (user_id, address, address_details, is_default)
            VALUES ($1, $2, $3::jsonb, $4)
            RETURNING id, user_id, address, address_details, is_default, created_at
            """,
            user_id, address, _to_json_str(address_details), is_default,
        )
        result = dict(row)
        result["address_details"] = _parse_jsonb(result["address_details"])
        return result


async def delete_user_address(address_id: int) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM user_addresses WHERE id = $1",
            address_id,
        )
        return result != "DELETE 0"


async def set_default_address(user_id: int, address_id: int) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE user_addresses SET is_default = FALSE WHERE user_id = $1",
                user_id,
            )
            result = await conn.execute(
                "UPDATE user_addresses SET is_default = TRUE WHERE id = $1 AND user_id = $2",
                address_id, user_id,
            )
        return result != "UPDATE 0"


async def seed_wheel_prizes():
    pool = await get_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval("SELECT COUNT(*) FROM wheel_prizes")
        if count == 0:
            await conn.executemany(
                "INSERT INTO wheel_prizes (name, weight) VALUES ($1, $2)",
                [
                    ("Суши Пончик в подарок!", 30),
                    ("Онигири в подарок!", 25),
                    ("Удон с курицей в подарок!", 20),
                    ("Суши торт в подарок!", 15),
                    ("Фортуна сет Классика в подарок!", 10),
                ],
            )
            logger.info("Wheel prizes seeded")


async def get_active_prizes() -> List[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, name, weight FROM wheel_prizes WHERE is_active = TRUE ORDER BY id"
        )
        return [dict(r) for r in rows]


async def can_spin(user_id: int) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COUNT(*) as cnt FROM wheel_spins "
            "WHERE user_id = $1 AND created_at::date = NOW()::date",
            user_id,
        )
        return row["cnt"] == 0


async def save_spin(user_id: int, prize_id: int, prize_name: str) -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO wheel_spins (user_id, prize_id, prize_name) "
            "VALUES ($1, $2, $3) RETURNING id, created_at",
            user_id, prize_id, prize_name,
        )
        return dict(row)


async def seed_promocodes():
    """
    Засеивает промокоды, соответствующие реальным SellKit-акциям Гедзы.

    is_hidden = TRUE — технические промокоды, не показываются в UI.
    auto_activate = FALSE — промокод не активируется автоматически,
                           пользователь активирует его кликом по купону.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval("SELECT COUNT(*) FROM promocodes")
        if count > 0:
            logger.info(f"Promocodes уже засеяны ({count} шт.)")
            return

        await conn.executemany(
            """
            INSERT INTO promocodes
                (code, discount, percent, min_order, description, title,
                 sale_type, promocode_type, delivery_types, auto_activate,
                 min_cart_price, gift_name, gift_picture, tag, is_active,
                 category_name, applies_to_category_only, is_hidden)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
            """,
            [
                # ─── Самовывоз: 10% при pickup ───
                # ⚡ auto_activate = FALSE — пользователь активирует кликом
                (
                    "Самовывоз", 0, 10, 0,
                    "ЗАБЕРИ САМ — 10% СКИДКИ",
                    "ЗАБЕРИ САМ — 10% СКИДКИ",
                    "price", 13, "1", False, 0,
                    None, None, "Самовывоз", True,
                    None, False,
                    False,
                ),
                # ─── Техническая акция (не показывается) ───
                (
                    "ПОПАЛ В КОРЗИНЕ", 0, 0, 0,
                    "Попал в корзине",
                    "Попал в корзине",
                    "price", 13, "2", True, 0,
                    None, None, "Промокод", True,
                    None, False,
                    True,
                ),
                # ─── СВОИ: подарок от 890 ₽ ───
                (
                    "СВОИ", 0, 0, 890,
                    "Суши торт с курицей в подарок от 890 ₽. Только для точек Черниковка/Сипайлово.",
                    "Суши торт в подарок к заказу от 890 руб.",
                    "gift", 14, "2", False, 890,
                    "Суши торт с курицей",
                    "https://placehold.co/200x200/d40000/ffffff?text=Sushi+Cake",
                    "СВОИ", True,
                    None, False,
                    False,
                ),
                # ─── ВИТРИНА 50: скидка 50% только на категорию «Витрина» ───
                (
                    "ВИТРИНА 50", 0, 50, 0,
                    "Витрина со скидкой 50%",
                    "Витрина со скидкой 50%",
                    "price", 2, "1", True, 0,
                    None, None, "Витрина", True,
                    "Витрина- забери за 15 минут", True,
                    False,
                ),
            ],
        )
        logger.info("Промокоды засеяны (4 шт.)")


async def find_promocode(code: str) -> Optional[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM promocodes WHERE code = $1 AND is_active = TRUE",
            code.upper() if code else "",
        )
        return dict(row) if row else None


async def upsert_user(user_id, username=None, first_name=None, last_name=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (user_id, username, first_name, last_name, last_seen)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                username   = COALESCE(EXCLUDED.username, users.username),
                first_name = COALESCE(EXCLUDED.first_name, users.first_name),
                last_name  = COALESCE(EXCLUDED.last_name, users.last_name),
                last_seen  = NOW(),
                updated_at = NOW()
            """,
            user_id, username, first_name, last_name,
        )


async def register_user(user_id, phone, address, legal_agreed=True, name='', address_details=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO users (user_id, name, phone, address, legal_agreed, address_details, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                name            = EXCLUDED.name,
                phone           = EXCLUDED.phone,
                address         = EXCLUDED.address,
                legal_agreed    = EXCLUDED.legal_agreed,
                address_details = EXCLUDED.address_details,
                updated_at      = NOW()
            RETURNING user_id, name, phone, address, legal_agreed, address_details, created_at
            """,
            user_id, name, phone, address, legal_agreed, _to_json_str(address_details),
        )
        if not row:
            return None
        result = dict(row)
        result["address_details"] = _parse_jsonb(result["address_details"])
        return result


async def get_user_profile(user_id: int) -> Optional[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT user_id, name, phone, address, legal_agreed, "
            "       address_details, consent_given, unsubscribed, created_at "
            "FROM users WHERE user_id = $1",
            user_id,
        )
        if not row:
            return None
        result = dict(row)
        result["address_details"] = _parse_jsonb(result["address_details"])
        return result


async def set_payment_type(user_id: int, payment_type: str) -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO user_payment_settings (user_id, payment_type, updated_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                payment_type = EXCLUDED.payment_type,
                updated_at = NOW()
            RETURNING user_id, payment_type
            """,
            user_id, payment_type,
        )
        return dict(row)


async def get_payment_type(user_id: int) -> str:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT payment_type FROM user_payment_settings WHERE user_id = $1",
            user_id,
        )
        return row["payment_type"] if row else "card_on_delivery"


async def set_order_time(user_id: int, order_time: str) -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO user_order_time (user_id, order_time, updated_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                order_time = EXCLUDED.order_time,
                updated_at = NOW()
            RETURNING user_id, order_time
            """,
            user_id, order_time,
        )
        return dict(row)


async def get_order_time(user_id: int) -> str:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT order_time FROM user_order_time WHERE user_id = $1",
            user_id,
        )
        return row["order_time"] if row else "now"