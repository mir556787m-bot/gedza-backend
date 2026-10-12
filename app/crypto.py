# app/crypto.py
"""
Шифрование чувствительных полей (ФЗ-152).

Использование:
  encrypted = encrypt_field("+7 999 123-45-67")
  plain = decrypt_field(encrypted)

Ключ генерируется ОДИН РАЗ и хранится в .env:
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
import os
import logging
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

DB_ENCRYPTION_KEY = os.getenv("DB_ENCRYPTION_KEY", "")

if not DB_ENCRYPTION_KEY:
    raise RuntimeError(
        "DB_ENCRYPTION_KEY не задан в .env. "
        "Сгенерируйте: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    )

try:
    fernet = Fernet(DB_ENCRYPTION_KEY.encode())
except Exception as e:
    raise RuntimeError(f"DB_ENCRYPTION_KEY невалиден: {e}")


def encrypt_field(plain: str) -> str:
    """Шифрует строку. Возвращает Base64-строку."""
    if plain is None:
        return None
    if not plain:
        return ""
    try:
        return fernet.encrypt(plain.encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.error(f"encrypt_field error: {e}")
        raise


def decrypt_field(cipher: str) -> str:
    """Расшифровывает Base64-строку. Возвращает plain."""
    if cipher is None:
        return None
    if not cipher:
        return ""
    try:
        return fernet.decrypt(cipher.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        logger.error("decrypt_field: InvalidToken — неверный ключ или данные")
        return ""
    except Exception as e:
        logger.error(f"decrypt_field error: {e}")
        return ""


def mask_phone(phone: str) -> str:
    """
    Маскирует телефон для отображения на фронте.
    +79991234567 → +7 (999) ***-45-67
    """
    if not phone:
        return ""
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 10:
        return phone
    return f"+{digits[0]} ({digits[1:4]}) ***-{digits[-4:-2]}-{digits[-2:]}"