"""Утилиты безопасности: JWT и хэширование паролей."""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Исправленная конфигурация для совместимости с bcrypt 4.1+
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__truncate_error=True,  # Обрезать пароли длиннее 72 байт
)

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 часа


def hash_password(password: str) -> str:
    """Захэшировать пароль."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверить пароль."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str, account_id: str | None = None) -> str:
    """Создать JWT-токен."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "exp": expire,
    }
    if account_id:
        payload["account_id"] = account_id
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Декодировать JWT-токен."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

def create_reset_token(user_id: str) -> str:
    """Создать токен для сброса пароля (действует 1 час)."""
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    payload = {"sub": user_id, "type": "reset", "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_reset_token(token: str) -> str | None:
    """Проверить токен сброса пароля. Возвращает user_id или None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "reset":
            return None
        return payload["sub"]
    except JWTError:
        return None