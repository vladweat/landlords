from http import HTTPStatus
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from loguru import logger

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import redis

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging_middleware import LoggingMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError


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
    )

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
        logger.warning(f"Application exception: {exc.message}", status_code=exc.status_code, path=request.url.path)
        return JSONResponse(status_code=exc.status_code, content={"status": "error", "message": exc.message})

    # Обработчик необработанных исключений
    @app.exception_handler(Exception)
    def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Обработать неожиданное исключение."""
        logger.exception("Unhandled exception: {}", str(exc), path=request.url.path)
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

            session = SessionLocal()
            session.execute(text("SELECT 1"))
            session.close()
        except Exception:
            return JSONResponse(status_code=503, content={"status": "error", "message": "db_unavailable"})

        # Check Redis
        try:
            r = redis.from_url(settings.REDIS_URL)
            if not r.ping():
                raise RuntimeError("redis_ping_failed")
        except Exception:
            return JSONResponse(status_code=503, content={"status": "error", "message": "redis_unavailable"})

        return JSONResponse(status_code=200, content={"status": "ok"})

    @app.get("/metrics")
    def metrics() -> Response:
        """Prometheus metrics endpoint."""
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
    from app.api.v1.routes.claims import router as claims_router

    app.include_router(auth_router)
    app.include_router(account_router)
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

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG, log_level=settings.LOG_LEVEL.lower())

