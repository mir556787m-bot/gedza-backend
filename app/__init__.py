# app/__init__.py
from pathlib import Path
from dotenv import load_dotenv

_env_local = Path(__file__).parent.parent / ".env.local"
if _env_local.exists():
    load_dotenv(_env_local, override=True, encoding="utf-8")
else:
    load_dotenv(encoding="utf-8")