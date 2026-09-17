# app/config.py
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MAX_BOT_TOKEN: str = ""
    MAX_API_URL: str = "https://platform-api2.max.ru"
    MAX_WEBHOOK_SECRET: str = ""

    MINI_APP_URL: str = ""
    MINI_APP_NAME: str = "gedza_delivery"

    REDIS_URL: str = "redis://localhost:6379/0"
    MENU_CACHE_TTL: int = 3600
    PARSE_INTERVAL_MINUTES: int = 60

    POSTGRES_URL: str = "postgresql://gedza:gedza@localhost:5432/gedza"

    GEDZA_URL: str = "https://gedzagroup.ru/"
    ADMIN_SECRET: str = ""

    class Config:
        env_file = ".env"


settings = Settings()