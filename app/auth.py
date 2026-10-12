# app/auth.py
import os, hmac, hashlib, json, logging, urllib.parse, secrets, time
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)
MAX_BOT_TOKEN = os.getenv("MAX_BOT_TOKEN", "")
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TTL_MIN = 15
JWT_REFRESH_TTL_DAYS = 7
INIT_DATA_MAX_AGE_SEC = int(os.getenv("INIT_DATA_MAX_AGE_SEC", "3600"))
SKIP_HMAC_CHECK = os.getenv("SKIP_HMAC_CHECK", "false").lower() == "true"

if not JWT_SECRET:
    JWT_SECRET = MAX_BOT_TOKEN or secrets.token_urlsafe(48)
if len(JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET < 32")

security = HTTPBearer(auto_error=False)

def validate_init_data(init_data):
    if not init_data or not MAX_BOT_TOKEN:
        return None
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None
        if SKIP_HMAC_CHECK:
            logger.warning("SKIP_HMAC_CHECK=true")
            return _finalize(parsed)
        sorted_items = sorted(parsed.items())
        launch_params = "\n".join(f"{k}={v}" for k, v in sorted_items)
        secret_key = hmac.new(MAX_BOT_TOKEN.encode(), b"WebAppData", hashlib.sha256).digest()
        computed_hash = hmac.new(secret_key, launch_params.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed_hash, received_hash):
            logger.warning("initData mismatch")
            return None
        return _finalize(parsed)
    except Exception as e:
        logger.error(f"initData error: {e}")
        return None

def _finalize(parsed):
    try:
        auth_date = int(parsed.get("auth_date", "0"))
    except Exception:
        return None
    if auth_date > 1e12:
        auth_date = auth_date / 1000
    age = time.time() - auth_date
    if age < 0 or age > INIT_DATA_MAX_AGE_SEC:
        return None
    return parsed

def extract_user_id(parsed):
    try:
        user_raw = parsed.get("user", "{}")
        user_info = json.loads(user_raw) if isinstance(user_raw, str) else user_raw
        uid = user_info.get("id")
        return int(uid) if uid else None
    except Exception:
        return None

def create_access_token(user_id, extra=None):
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": int(now.timestamp()), "exp": int((now + timedelta(minutes=JWT_ACCESS_TTL_MIN)).timestamp()), "type": "access", "jti": secrets.token_urlsafe(16), "iss": "gedza-max-bot", "aud": "gedza-mini-app"}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id):
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": int(now.timestamp()), "exp": int((now + timedelta(days=JWT_REFRESH_TTL_DAYS)).timestamp()), "type": "refresh", "jti": secrets.token_urlsafe(16), "iss": "gedza-max-bot", "aud": "gedza-mini-app"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token, expected_type="access"):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], audience="gedza-mini-app", issuer="gedza-max-bot", options={"require": ["exp", "iat", "sub", "type"]})
        if payload.get("type") != expected_type:
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

async def get_current_user(request: Request, credentials=Depends(security)) -> int:
    if not credentials:
        raise HTTPException(401, "Authorization header required", headers={"WWW-Authenticate": "Bearer"})
    payload = decode_token(credentials.credentials, expected_type="access")
    if not payload:
        raise HTTPException(401, "Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})
    try:
        return int(payload["sub"])
    except Exception:
        raise HTTPException(401, "Malformed token subject")
