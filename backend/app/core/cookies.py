"""HttpOnly-cookie с JWT. Bearer в заголовке остаётся для тестов и API-клиентов."""

from fastapi import Response

from app.core.config import settings
from app.core.security import ACCESS_TOKEN_EXPIRE_MINUTES

ACCESS_TOKEN_COOKIE = "access_token"


def set_access_cookie(response: Response, token: str) -> None:
    """Положить JWT в HttpOnly-cookie. JS его не читает."""
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=token,
        httponly=True,
        secure=settings.APP_ENV == "production",
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"


def clear_access_cookie(response: Response) -> None:
    """Сбросить cookie сессии."""
    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE,
        path="/",
        httponly=True,
        secure=settings.APP_ENV == "production",
        samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"
