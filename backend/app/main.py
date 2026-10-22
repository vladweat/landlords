from http import HTTPStatus
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import redis
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from loguru import logger
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.core.config import settings
from app.core.cookies import ACCESS_TOKEN_COOKIE
from app.core.exceptions import AppException
from app.core.logging_middleware import LoggingMiddleware, _safe_request_path


def _origin(value: str | None) -> str | None:
    """Нормализовать HTTP(S) origin, учитывая стандартные порты."""
    parsed = urlsplit(value or "")
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        return None
    scheme = parsed.scheme.lower()
    host = parsed.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    try:
        port = parsed.port
    except ValueError:
        return None
    default_port = 443 if scheme == "https" else 80
    authority = host if port is None or port == default_port else f"{host}:{port}"
    return f"{scheme}://{authority}"


def _sanitize_sentry_event(event: dict[str, Any], hint: object = None) -> dict[str, Any]:
    """Очистить telemetry от capability URL и заголовков с credentials."""
    request = event.get("request")
    if isinstance(request, dict):
        url = request.get("url")
        if isinstance(url, str):
            parsed = urlsplit(url)
            request["url"] = urlunsplit(
                (
                    parsed.scheme,
                    parsed.netloc,
                    _safe_request_path(parsed.path),
                    "",
                    "",
                )
            )
        request.pop("query_string", None)
        request.pop("data", None)
        request.pop("cookies", None)
        headers = request.get("headers")
        if isinstance(headers, dict):
            for key in list(headers):
                if key.lower() in {"authorization", "cookie", "set-cookie"}:
                    headers.pop(key, None)

    transaction = event.get("transaction")
    if isinstance(transaction, str):
        method, separator, path = transaction.partition(" ")
        if separator:
            event["transaction"] = f"{method} {_safe_request_path(path.split('?', 1)[0])}"
        else:
            event["transaction"] = _safe_request_path(transaction.split("?", 1)[0])
    return event


def _init_sentry() -> None:
    """Инициализировать Sentry, если задан SENTRY_DSN."""
    if not settings.SENTRY_DSN:
        return

    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.APP_ENV,
        release=settings.APP_VERSION,
        integrations=[FastApiIntegration(), CeleryIntegration(), SqlalchemyIntegration()],
        traces_sample_rate=0.1 if settings.APP_ENV == "production" else 0.0,
        send_default_pii=False,
        before_send=_sanitize_sentry_event,
        before_send_transaction=_sanitize_sentry_event,
    )


def create_app() -> FastAPI:
    """
    Создать и сконфигурировать экземпляр FastAPI.

    Returns:
        Сконфигурированное приложение FastAPI.
    """
    _init_sentry()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
    )

    @app.middleware("http")
    async def cookie_csrf_protection(request: Request, call_next):
        """Проверить Origin для небезопасных запросов с cookie-аутентификацией."""
        safe_methods = {"GET", "HEAD", "OPTIONS"}
        authorization = request.headers.get("authorization", "")
        has_bearer = authorization.lower().startswith("bearer ")
        has_cookie = request.cookies.get(ACCESS_TOKEN_COOKIE) is not None
        if request.method not in safe_methods and has_cookie and not has_bearer:
            origin = request.headers.get("origin")
            expected_origin = _origin(settings.FRONTEND_URL)
            request_origin = _origin(origin)
            origin_path = urlsplit(origin or "").path
            if (
                not expected_origin
                or request_origin != expected_origin
                or origin_path not in {"", "/"}
            ):
                return JSONResponse(
                    status_code=403,
                    content={"status": "error", "message": "Cross-site request blocked"},
                )
        return await call_next(request)

    # Middleware
    app.add_middleware(LoggingMiddleware)

    # Обработчик ошибок валидации
    @app.exception_handler(RequestValidationError)
    def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"status": "error", "message": "Validation error", "details": exc.errors()},
        )

    # Глобальный обработчик кастомных исключений
    @app.exception_handler(AppException)
    def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        """Обработать кастомное исключение приложения."""
        logger.warning(
            f"Application exception: {exc.message}",
            status_code=exc.status_code,
            path=_safe_request_path(request.url.path),
        )
        return JSONResponse(status_code=exc.status_code, content={"status": "error", "message": exc.message})

    # Обработчик необработанных исключений
    @app.exception_handler(Exception)
    def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Обработать неожиданное исключение."""
        logger.exception(
            "Unhandled exception: {}",
            str(exc),
            path=_safe_request_path(request.url.path),
        )
        return JSONResponse(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, content={"status": "error", "message": "Internal server error"})

    # Healthcheck
    @app.get("/health", tags=["System"])
    def healthcheck() -> dict[str, str]:
        """Проверка работоспособности сервиса."""
        return {"status": "ok"}

    @app.get("/ready", tags=["System"])
    def readiness() -> JSONResponse:
        """Readiness check: DB and Redis connectivity."""
        # Check DB
        from app.db.session import SessionLocal

        try:
            from sqlalchemy import text

            with SessionLocal() as session:
                session.execute(text("SELECT 1"))
        except Exception:
            return JSONResponse(status_code=503, content={"status": "error", "message": "db_unavailable"})

        # Check Redis
        try:
            r = redis.from_url(settings.REDIS_URL)
            if not r.ping():
                raise RuntimeError("redis_ping_failed")
        except Exception:
            return JSONResponse(status_code=503, content={"status": "error", "message": "redis_unavailable"})

        # Beat stale → алерт (дедуп); readiness по DB/Redis не ломаем.
        try:
            from app.services.ops_alert_service import check_and_alert_beat_stale, update_ops_gauges

            update_ops_gauges()
            check_and_alert_beat_stale()
        except Exception:
            logger.exception("ops beat check failed during readiness")

        return JSONResponse(status_code=200, content={"status": "ok"})

    @app.get("/metrics")
    def metrics() -> Response:
        """Prometheus metrics endpoint."""
        try:
            from app.services.ops_alert_service import update_ops_gauges

            update_ops_gauges()
        except Exception:
            logger.exception("ops gauges update failed")
        data = generate_latest()
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)

    from app.api.v1.routes.auth import router as auth_router
    from app.api.v1.routes.account import router as account_router
    from app.api.v1.routes.properties import router as properties_router
    from app.api.v1.routes.tenants import router as tenants_router
    from app.api.v1.routes.contracts import router as contracts_router
    from app.api.v1.routes.contract_templates import router as contract_templates_router
    from app.api.v1.routes.charges import router as charges_router
    from app.api.v1.routes.payments import router as payments_router
    from app.api.v1.routes.expenses import router as expenses_router
    from app.api.v1.routes.dashboard import router as dashboard_router
    from app.api.v1.routes.calendar import router as calendar_router
    from app.api.v1.routes.documents import router as documents_router
    from app.api.v1.routes.reminders import router as reminders_router
    from app.api.v1.routes.feedback import router as feedback_router
    from app.api.v1.routes.notifications import router as notifications_router
    from app.api.v1.routes.reports import router as reports_router
    from app.api.v1.routes.public_invoices import router as public_invoices_router
    from app.api.v1.routes.public_invites import router as public_invites_router
    from app.api.v1.routes.public_portal import router as public_portal_router
    from app.api.v1.routes.public_status import router as public_status_router
    from app.api.v1.routes.claims import router as claims_router
    from app.api.v1.routes.billing import router as billing_router

    app.include_router(auth_router)
    app.include_router(account_router)
    app.include_router(billing_router)
    app.include_router(properties_router)
    app.include_router(tenants_router)
    app.include_router(contracts_router)
    app.include_router(contract_templates_router)
    app.include_router(charges_router)
    app.include_router(payments_router)
    app.include_router(claims_router)
    app.include_router(expenses_router)
    app.include_router(dashboard_router)
    app.include_router(calendar_router)
    app.include_router(documents_router)
    app.include_router(reminders_router)
    app.include_router(feedback_router)
    app.include_router(notifications_router)
    app.include_router(reports_router)
    app.include_router(public_invoices_router)
    app.include_router(public_invites_router)
    app.include_router(public_portal_router)
    app.include_router(public_status_router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG, log_level=settings.LOG_LEVEL.lower())

