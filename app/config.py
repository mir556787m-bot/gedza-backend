# app/config.py
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # === MAX Bot ===
    MAX_BOT_TOKEN: str = ""
    MAX_API_URL: str = "https://platform-api2.max.ru"
    MAX_WEBHOOK_SECRET: str = ""

    # === Mini App ===
    MINI_APP_URL: str = ""
    MINI_APP_NAME: str = "se14144667_1_bot"

    # === Redis ===
    REDIS_URL: str = "redis://localhost:6379/0"
    MENU_CACHE_TTL: int = 3600
    PARSE_INTERVAL_MINUTES: int = 60

    # === PostgreSQL ===
    POSTGRES_URL: str = "postgresql://gedza:gedza@localhost:5432/gedza"
    POSTGRES_PASSWORD: str = ""

    # === Парсинг ===
    GEDZA_URL: str = "https://gedzagroup.ru/"

    # === Источник меню ===
    MENU_SOURCE: str = "parser"

    # === SellKit API ===
    SELLKIT_API_URL: str = "https://all.s2.sellkit.ru/NewApi"
    SELLKIT_AUTH_TOKEN: str = ""
    SELLKIT_DEVICE_ID: str = ""
    SELLKIT_ORG_ID: str = "2"
    SELLKIT_ENABLED: bool = False

    # === iiko API ===
    IIKO_API_LOGIN: str = ""
    IIKO_ORG_ID: str = ""
    IIKO_TERMINAL_GROUP_ID: str = ""
    IIKO_SOURCE_KEY: str = "max_bot"
    IIKO_ENABLED: bool = False

    # === Админ ===
    ADMIN_SECRET: str = ""

    # === Безопасность ===
    JWT_SECRET: str = ""
    DB_ENCRYPTION_KEY: str = ""
    ALLOW_QUERY_USER_ID: bool = False

    # === Внутренний webhook ===
    INTERNAL_SECRET_TOKEN: str = ""

    class Config:
        env_file = ".env.local"        # ⚡ читаем из .env.local
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()